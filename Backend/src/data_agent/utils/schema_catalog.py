"""Schema catalog: cached, compact, question-scoped schema context for SQL generation.

Replaces the old approach of introspecting the whole database on every request and
pasting every table plus 5 raw sample rows into the prompt. Differences:

* Introspected once and cached (TTL), using 3 queries total instead of 1 + 2N per request.
* Columns come back in ``ordinal_position`` order and are filtered by schema.
* PK / FK relationships are included, so the model can join without guessing.
* No raw sample rows (they leak PII into the prompt and are a prompt-injection surface).
  Instead, low-cardinality text columns get a short ``e.g.`` hint taken from planner
  statistics (``pg_stats``) -- no table scans, and sensitive-looking columns are skipped.
* A character budget: if the full schema fits, everything is sent; otherwise only the
  tables relevant to the question (plus their FK neighbours) are sent.
* Introspection failures raise ``SchemaUnavailableError``; error text is never placed
  into a prompt as if it were schema.
"""

from __future__ import annotations

import contextlib
import logging
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Sequence

import psycopg2

from data_agent.config import settings

logger = logging.getLogger(__name__)

_MAX_SEED_TABLES = 5
_SEED_SCORE_FRACTION = 0.4
_MAX_HINT_VALUE_LEN = 40
_MAX_HIDDEN_NAMES = 50
_REFRESH_BACKOFF_SECONDS = 30


class SchemaUnavailableError(RuntimeError):
    """The database schema could not be read. Never feed this text to an LLM."""


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Column:
    name: str
    data_type: str
    is_pk: bool = False
    references: tuple[str, str] | None = None  # (table, column) for single-column FKs
    example_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[Column, ...]
    composite_fks: tuple[str, ...] = ()  # e.g. "(a, b) -> other(x, y)"


@dataclass(frozen=True)
class SchemaCatalog:
    schema: str
    tables: tuple[Table, ...]
    loaded_at: float = field(default_factory=time.monotonic)
    # table -> tables it references or is referenced by (undirected)
    adjacency: dict[str, frozenset[str]] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Introspection
# --------------------------------------------------------------------------- #
_COLUMNS_SQL = """
SELECT c.table_name, c.column_name, c.data_type, c.udt_name
FROM information_schema.columns c
JOIN information_schema.tables t
  ON t.table_schema = c.table_schema AND t.table_name = c.table_name
WHERE c.table_schema = %s AND t.table_type IN ('BASE TABLE', 'VIEW')
ORDER BY c.table_name, c.ordinal_position
"""

_KEYS_SQL = """
SELECT con.contype::text,
       cl.relname::text,
       ARRAY(SELECT a.attname::text
             FROM unnest(con.conkey) WITH ORDINALITY k(attnum, ord)
             JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum
             ORDER BY k.ord),
       fcl.relname::text,
       ARRAY(SELECT a.attname::text
             FROM unnest(con.confkey) WITH ORDINALITY k(attnum, ord)
             JOIN pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = k.attnum
             ORDER BY k.ord)
FROM pg_constraint con
JOIN pg_class cl ON cl.oid = con.conrelid
JOIN pg_namespace ns ON ns.oid = cl.relnamespace
LEFT JOIN pg_class fcl ON fcl.oid = con.confrelid
WHERE ns.nspname = %s AND con.contype IN ('p', 'f')
"""

# pg_stats only exposes columns the current role can read, and needs no table scan.
_HINTS_SQL = """
SELECT s.tablename::text, s.attname::text, s.n_distinct, s.most_common_vals::text::text[]
FROM pg_stats s
WHERE s.schemaname = %s AND s.most_common_vals IS NOT NULL
"""

_TYPE_ALIASES = {
    "character varying": "varchar",
    "character": "char",
    "integer": "int",
    "double precision": "float8",
    "timestamp without time zone": "timestamp",
    "timestamp with time zone": "timestamptz",
    "time without time zone": "time",
    "time with time zone": "timetz",
}
_TEXT_TYPES = {"character varying", "character", "text", "USER-DEFINED"}
_SENSITIVE_COLUMN = re.compile(
    r"(e?mail|phone|mobile|name|address|street|plate|passport|ssn|tax_?id|token|"
    r"secret|passw|card|iban|account|dob|birth|licen[sc]e|ip_?addr)",
    re.IGNORECASE,
)


def _connect():
    return psycopg2.connect(
        host=settings.DB_host,
        port=settings.DB_port,
        user=settings.DB_user,
        password=settings.DB_password,
        dbname=settings.DB_name,
        connect_timeout=5,
        options="-c statement_timeout=10000 -c default_transaction_read_only=on",
    )


def _short_type(data_type: str, udt_name: str) -> str:
    if data_type == "ARRAY":
        return f"{udt_name.lstrip('_')}[]"
    if data_type == "USER-DEFINED":
        return udt_name
    return _TYPE_ALIASES.get(data_type, data_type)


def _build_catalog(
    schema: str,
    column_rows: Iterable[tuple],
    key_rows: Iterable[tuple],
    hint_rows: Iterable[tuple],
    max_hint_values: int,
) -> SchemaCatalog:
    """Pure function (no DB access): assemble a catalog from raw introspection rows."""
    pks: dict[str, set[str]] = defaultdict(set)
    single_fk: dict[tuple[str, str], tuple[str, str]] = {}
    composite_fks: dict[str, list[str]] = defaultdict(list)
    edges: dict[str, set[str]] = defaultdict(set)

    for kind, table, cols, ref_table, ref_cols in key_rows:
        if kind == "p":
            pks[table].update(cols)
        elif kind == "f" and ref_table:
            edges[table].add(ref_table)
            edges[ref_table].add(table)
            if len(cols) == 1 and len(ref_cols) == 1:
                single_fk[(table, cols[0])] = (ref_table, ref_cols[0])
            else:
                composite_fks[table].append(
                    f"({', '.join(cols)}) -> {ref_table}({', '.join(ref_cols)})"
                )

    hints: dict[tuple[str, str], tuple[str, ...]] = {}
    for table, column, n_distinct, values in hint_rows:
        # n_distinct > 0 is an absolute distinct count; <= 0 means "scales with row count".
        if n_distinct is None or not (0 < n_distinct <= max_hint_values) or not values:
            continue
        if _SENSITIVE_COLUMN.search(column):
            continue
        kept = tuple(v for v in values[:max_hint_values] if v and len(v) <= _MAX_HINT_VALUE_LEN)
        if kept:
            hints[(table, column)] = kept

    by_table: dict[str, list[Column]] = defaultdict(list)
    for table, column, data_type, udt_name in column_rows:
        is_pk = column in pks.get(table, ())
        ref = single_fk.get((table, column))
        examples: tuple[str, ...] = ()
        if data_type in _TEXT_TYPES and not is_pk and ref is None:
            examples = hints.get((table, column), ())
        by_table[table].append(
            Column(column, _short_type(data_type, udt_name), is_pk, ref, examples)
        )

    tables = tuple(
        Table(name, tuple(cols), tuple(composite_fks.get(name, ())))
        for name, cols in sorted(by_table.items())
    )
    known = {t.name for t in tables}
    adjacency = {
        t.name: frozenset(n for n in edges.get(t.name, ()) if n in known and n != t.name)
        for t in tables
    }
    return SchemaCatalog(schema=schema, tables=tables, adjacency=adjacency)


def load_catalog(schema: str) -> SchemaCatalog:
    """Introspect ``schema`` with a read-only, time-limited connection (3 queries)."""
    try:
        with contextlib.closing(_connect()) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(_COLUMNS_SQL, (schema,))
                column_rows = cur.fetchall()
                cur.execute(_KEYS_SQL, (schema,))
                key_rows = cur.fetchall()
                hint_rows: list[tuple] = []
                if settings.schema_value_hints:
                    cur.execute(_HINTS_SQL, (schema,))
                    hint_rows = cur.fetchall()
    except psycopg2.Error as exc:
        # Full detail goes to the server log only; the message may reach API clients.
        logger.error("Schema introspection failed for '%s': %s", schema, exc)
        raise SchemaUnavailableError("The database schema is currently unavailable.") from exc

    if not column_rows:
        raise SchemaUnavailableError(
            f"No tables found in schema '{schema}' (wrong DB_SCHEMA, or the role lacks privileges)."
        )
    return _build_catalog(schema, column_rows, key_rows, hint_rows, settings.schema_hint_max_values)


# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #
class _CatalogCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._catalog: SchemaCatalog | None = None
        self._retry_at = 0.0

    def get(self, schema: str, ttl: float, force: bool = False) -> SchemaCatalog:
        with self._lock:  # one loader at a time; waiters reuse its result
            now = time.monotonic()
            cached = self._catalog if self._catalog and self._catalog.schema == schema else None
            if cached and not force:
                if now - cached.loaded_at < ttl or now < self._retry_at:
                    return cached
            try:
                fresh = load_catalog(schema)
            except SchemaUnavailableError:
                if cached:
                    logger.warning("Schema refresh failed; serving stale catalog for '%s'.", schema)
                    self._retry_at = now + _REFRESH_BACKOFF_SECONDS
                    return cached
                raise
            self._catalog = fresh
            self._retry_at = 0.0
            return fresh


_cache = _CatalogCache()


def get_schema_catalog(schema: str | None = None) -> SchemaCatalog:
    return _cache.get(schema or settings.DB_schema, settings.schema_cache_ttl)


def refresh_schema_catalog(schema: str | None = None) -> SchemaCatalog:
    """Force a reload (e.g. after a migration) instead of waiting for the TTL."""
    return _cache.get(schema or settings.DB_schema, settings.schema_cache_ttl, force=True)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _ident(name: str) -> str:
    if re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        return name
    return '"' + name.replace('"', '""') + '"'


def _literal(value: str) -> str:
    return "'" + re.sub(r"\s+", " ", value).replace("'", "''") + "'"


def render_table(table: Table) -> str:
    lines = [f"TABLE {_ident(table.name)}"]
    for col in table.columns:
        parts = [f"  {_ident(col.name)} {col.data_type}"]
        if col.is_pk:
            parts.append("PK")
        if col.references:
            parts.append(f"FK->{_ident(col.references[0])}.{_ident(col.references[1])}")
        if col.example_values:
            parts.append("-- e.g. " + ", ".join(_literal(v) for v in col.example_values))
        lines.append(" ".join(parts))
    lines.extend(f"  FK {fk}" for fk in table.composite_fks)
    return "\n".join(lines)


def render_schema(tables: Sequence[Table], schema: str, hidden: Sequence[str] = ()) -> str:
    out = f"Schema: {schema}\n\n" + "\n\n".join(render_table(t) for t in tables)
    if hidden:
        shown = ", ".join(_ident(h) for h in hidden[:_MAX_HIDDEN_NAMES])
        more = " ..." if len(hidden) > _MAX_HIDDEN_NAMES else ""
        out += f"\n\nOther tables not shown: {shown}{more}"
    return out


# --------------------------------------------------------------------------- #
# Question-scoped table selection (schema linking)
# --------------------------------------------------------------------------- #
_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "id the of an in on by per for and or to with what which how many much show list all "
    "get give me is are was were from at as it its be this that there their do does".split()
)


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _tokens(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(text.lower()) if len(w) > 1 and w not in _STOPWORDS}


def _score(table: Table, question_tokens: set[str]) -> float:
    score = 3.0 * len(question_tokens & _tokens(table.name))
    for col in table.columns:
        score += 1.0 * len(question_tokens & _tokens(col.name))
        for value in col.example_values:
            score += 2.0 * len(question_tokens & _tokens(value))
    return score


def select_tables(
    catalog: SchemaCatalog, question: str, max_chars: int
) -> tuple[list[Table], list[str]]:
    """Return (tables to show, names of tables left out).

    If the whole schema fits in ``max_chars`` everything is shown. Otherwise tables are
    ranked by lexical overlap with the question, expanded with their FK neighbours (so
    joins stay possible), and packed into the budget. Lexical matching misses synonyms
    ("trips" vs ``rides``); swap in embeddings here if the schema gets large.
    """
    all_tables = list(catalog.tables)
    if len(render_schema(all_tables, catalog.schema)) <= max_chars:
        return all_tables, []

    by_name = {t.name: t for t in all_tables}
    q_tokens = _tokens(question)
    ranked = sorted(((_score(t, q_tokens), t) for t in all_tables), key=lambda x: (-x[0], x[1].name))
    matched = [(score, t) for score, t in ranked if score > 0]
    # A generic column (e.g. "amount") appears in many tables; only keep seeds that score
    # reasonably close to the best match so such ties don't crowd out relevant tables.
    cutoff = max(1.0, _SEED_SCORE_FRACTION * matched[0][0]) if matched else 0.0
    seeds = [t for score, t in matched if score >= cutoff][:_MAX_SEED_TABLES]

    ordered: list[Table] = []
    seen: set[str] = set()

    def add(t: Table) -> None:
        if t.name not in seen:
            seen.add(t.name)
            ordered.append(t)

    for t in seeds:
        add(t)
    for t in seeds:
        for neighbour in sorted(catalog.adjacency.get(t.name, ())):
            add(by_name[neighbour])
    if not ordered:  # nothing matched: fall back to the best-connected tables
        for t in sorted(all_tables, key=lambda t: (-len(catalog.adjacency.get(t.name, ())), t.name)):
            add(t)

    chosen: list[Table] = []
    used = len(f"Schema: {catalog.schema}\n\n")
    for t in ordered:
        size = len(render_table(t)) + 2
        if chosen and used + size > max_chars:
            continue
        chosen.append(t)
        used += size

    chosen_names = {t.name for t in chosen}
    chosen.sort(key=lambda t: t.name)  # stable ordering keeps the prompt prefix cache-friendly
    hidden = [t.name for t in all_tables if t.name not in chosen_names]
    return chosen, hidden


def build_schema_context(question: str, schema: str | None = None) -> tuple[str, list[str]]:
    """Schema text for the SQL prompt plus the names of the tables it covers."""
    catalog = get_schema_catalog(schema)
    tables, hidden = select_tables(catalog, question, settings.schema_max_chars)
    return render_schema(tables, catalog.schema, hidden), [t.name for t in tables]