import csv
from pathlib import Path
import os
import uuid

import requests
import streamlit as st

try:
    import pandas as pd
except ImportError:
    pd = None


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Database Agent",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Database Agent")
st.caption(
    "Ask questions about your database using natural language, or explore source datasets."
)


# --------------------------------------------------
# Data folder discovery helper
# --------------------------------------------------


def find_data_directory() -> Path | None:
    """Find the data directory containing CSV files across common project layouts."""
    frontend_dir = Path(__file__).resolve().parent
    candidates = [
        frontend_dir / "data",
    ]
    for p in candidates:
        if p.is_dir() and any(p.glob("*.csv")):
            return p
    return None


@st.cache_data(show_spinner=False)
def load_csv_data(file_path: str, max_rows: int = 1000):
    """Load CSV into a pandas DataFrame (or fallback list of dicts)."""
    if pd is not None:
        try:
            total_rows = (
                sum(1 for _ in open(file_path, encoding="utf-8", errors="ignore")) - 1
            )
        except Exception:
            total_rows = None

        df = pd.read_csv(file_path, nrows=max_rows)
        return df, total_rows
    else:
        rows = []
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            for i, r in enumerate(reader):
                if i < max_rows:
                    rows.append(r)
        return rows, len(rows)


# --------------------------------------------------
# Session state
# --------------------------------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:
    st.header("Settings")

    default_backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    backend_url = default_backend_url.strip().rstrip("/")

    show_sql = st.toggle(
        "Show generated SQL",
        value=True,
    )

    show_execution_result = st.toggle(
        "Show SQL execution result",
        value=False,
    )

    st.divider()

    st.caption("Conversation")
    st.code(st.session_state.thread_id, language=None)

    if st.button("New conversation", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.chat_history = []
        st.rerun()

    st.divider()


# --------------------------------------------------
# Main Navigation Tabs
# --------------------------------------------------

tab_chat, tab_tables, tab_erd = st.tabs(
    ["💬 Chat Agent", "📁 Database Tables", "🗺️ ER Diagram"]
)


# ==================================================
# TAB 1: Chat Agent
# ==================================================

with tab_chat:
    with st.container(height=500):
        for item in st.session_state.chat_history:
            with st.chat_message("user"):
                st.markdown(item["question"])

            with st.chat_message("assistant"):
                if item.get("error"):
                    st.error(item["error"])
                else:
                    st.markdown(item.get("final_answer") or "No answer returned.")

                    with st.expander("Query details"):
                        st.write("**Safety decision**")
                        safety = item.get("is_safe", "No")
                        if safety == "Yes":
                            st.success("Approved by SQL judge")
                        else:
                            st.warning(f"Not approved: {safety}")

                        st.write("**Judge comments**")
                        st.write(item.get("comments") or "No comments returned.")

                        if show_sql:
                            st.write("**Generated SQL**")
                            sql = item.get("generated_sql_query")
                            if sql:
                                st.code(sql, language="sql")
                            else:
                                st.info("No SQL query was returned.")

                        if show_execution_result:
                            st.write("**SQL execution result**")
                            st.code(
                                str(item.get("sql_query_execution_result", "")),
                                language="text",
                            )

    question = st.chat_input("Ask a question about your database...")

    if question:
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing your question..."):
                try:
                    response = requests.post(
                        f"{backend_url}/query",
                        json={
                            "user_input": question,
                            "thread_id": st.session_state.thread_id,
                        },
                        timeout=120,
                    )

                    if response.ok:
                        result = response.json()

                        if result.get("final_answer"):
                            st.markdown(result["final_answer"])
                        else:
                            st.warning("The backend returned no final answer.")

                        with st.expander("Query details"):
                            safety = result.get("is_safe", "No")

                            st.write("**Safety decision**")
                            if safety == "Yes":
                                st.success("Approved by SQL judge")
                            else:
                                st.warning(f"Not approved: {safety}")

                            st.write("**Judge comments**")
                            st.write(result.get("comments") or "No comments returned.")

                            if show_sql:
                                st.write("**Generated SQL**")
                                sql = result.get("generated_sql_query")
                                if sql:
                                    st.code(sql, language="sql")
                                else:
                                    st.info("No SQL query was returned.")

                            if show_execution_result:
                                st.write("**SQL execution result**")
                                st.code(
                                    str(result.get("sql_query_execution_result", "")),
                                    language="text",
                                )

                        st.session_state.chat_history.append(
                            {
                                "question": question,
                                "final_answer": result.get("final_answer", ""),
                                "is_safe": result.get("is_safe", "No"),
                                "comments": result.get("comments", ""),
                                "generated_sql_query": result.get(
                                    "generated_sql_query", ""
                                ),
                                "sql_query_execution_result": result.get(
                                    "sql_query_execution_result", ""
                                ),
                            }
                        )

                    else:
                        try:
                            detail = response.json().get("detail", response.text)
                        except ValueError:
                            detail = response.text

                        error_message = (
                            f"Backend returned HTTP {response.status_code}: {detail}"
                        )
                        st.error(error_message)

                        st.session_state.chat_history.append(
                            {
                                "question": question,
                                "error": error_message,
                            }
                        )

                except requests.exceptions.Timeout:
                    error_message = (
                        "The request timed out. The agent may still be "
                        "processing your question. Please try again."
                    )
                    st.error(error_message)

                    st.session_state.chat_history.append(
                        {
                            "question": question,
                            "error": error_message,
                        }
                    )

                except requests.exceptions.ConnectionError:
                    error_message = (
                        "Could not connect to the FastAPI backend. "
                        "Make sure your backend is running."
                    )
                    st.error(error_message)

                    st.session_state.chat_history.append(
                        {
                            "question": question,
                            "error": error_message,
                        }
                    )

                except (requests.exceptions.RequestException, ValueError) as exc:
                    error_message = f"Request failed: {exc}"
                    st.error(error_message)

                    st.session_state.chat_history.append(
                        {
                            "question": question,
                            "error": error_message,
                        }
                    )

        st.rerun()


# ==================================================
# TAB 2: Database Tables Viewer
# ==================================================

with tab_tables:
    st.subheader("📁 Database Tables & Sample Records")
    st.caption("Inspect the source datasets loaded into the database.")

    data_dir = find_data_directory()

    if not data_dir or not data_dir.is_dir():
        st.warning("Could not find the `data/` folder containing CSV tables.")
    else:
        csv_files = sorted(data_dir.glob("*.csv"))

        if not csv_files:
            st.info("No CSV files found in the data directory.")
        else:
            table_names = [f.stem for f in csv_files]

            selected_table_name = st.selectbox(
                "Select Table",
                options=table_names,
                index=0,
                format_func=lambda name: f"📋 {name} ({name}.csv)",
            )

            selected_file = data_dir / f"{selected_table_name}.csv"

            row_limit = st.slider(
                "Preview Rows",
                min_value=10,
                max_value=500,
                value=50,
                step=10,
            )

            data, total_rows = load_csv_data(str(selected_file), max_rows=row_limit)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Table", selected_table_name)
            with col2:
                if total_rows is not None:
                    st.metric("Total Rows in File", f"{total_rows:,}")
                else:
                    st.metric("Loaded Rows", f"{len(data):,}")
            with col3:
                num_cols = (
                    len(data.columns)
                    if pd is not None and hasattr(data, "columns")
                    else (len(data[0].keys()) if data else 0)
                )
                st.metric("Columns", num_cols)

            st.divider()

            if pd is not None and isinstance(data, pd.DataFrame):
                st.dataframe(data, use_container_width=True)

                with st.expander("Column Details & Data Types"):
                    type_info = pd.DataFrame(
                        {
                            "Column Name": data.columns,
                            "Detected Type": [str(t) for t in data.dtypes],
                            "Non-Null Count": data.notnull().sum().values,
                        }
                    )
                    st.dataframe(type_info, use_container_width=True)
            else:
                st.dataframe(data, use_container_width=True)


# ==================================================
# TAB 3: ER Diagram
# ==================================================

with tab_erd:
    st.subheader("🗺️ Entity Relationship (ER) Diagram")

    erd_candidates = [
        Path(__file__).resolve().parent / "ER_diagram" / "db_erd.png",
    ]
    erd_file = next((p for p in erd_candidates if p.is_file()), None)

    if erd_file:
        try:
            st.image(
                str(erd_file),
                use_container_width=True,
            )
        except TypeError:
            st.image(
                str(erd_file),
                use_column_width=True,
            )
    else:
        st.warning(
            "Could not find `db_erd.png` inside the `Frontend/ER_diagram` directory."
        )
