
import os
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in Backend directory, project root, and cwd
_current_file = Path(__file__).resolve()
_backend_dir = _current_file.parents[2]
_project_root = _current_file.parents[3]

load_dotenv(_backend_dir / ".env")
load_dotenv(_project_root / ".env")
load_dotenv()


class Settings:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")

        self.groq_model_api_base = os.getenv(
            "GROQ_API_BASE", "https://api.groq.com/openai/v1"
        )

        self.groq_model1 = os.getenv("GROQ_MODEL_HIGH", "openai/gpt-oss-120b")
        self.groq_model2 = os.getenv("GROQ_MODEL_LOW", "openai/gpt-oss-20b")
        self.groq_guardrail_model=os.getenv(
            "GROQ_GUARDRAIL_MODEL", "qwen/qwen3.8-27b"
        )

        # CORS allowed origins
        raw_origins = os.getenv(
            "FRONTEND_URL", "http://127.0.0.1:8001,http://localhost:8501"
        )
        self.allowed_origins: list[str] = [
            url.strip() for url in raw_origins.split(",") if url.strip()
        ]

        # DB config

        self.DB_host = os.getenv("DB_HOST", "localhost")
        self.DB_port = int(os.getenv("DB_PORT", "5432"))
        self.DB_name = os.getenv("DB_NAME", "data_agent_db")
        self.DB_user = os.getenv("DB_USER", "postgres")
        self.DB_password = os.getenv("DB_PASSWORD")
        self.DB_schema = os.getenv("DB_SCHEMA", "public")


        # Schema context (what gets sent to the SQL-generation prompt)
        self.schema_cache_ttl = int(os.getenv("SCHEMA_CACHE_TTL_SECONDS", "300"))
        self.schema_max_chars = int(os.getenv("SCHEMA_MAX_CHARS", "12000"))  # ~3k tokens
        self.schema_value_hints = os.getenv("SCHEMA_VALUE_HINTS", "true").lower() in ("1", "true", "yes")
        self.schema_hint_max_values = int(os.getenv("SCHEMA_HINT_MAX_VALUES", "12"))



        self.max_messages=int(os.getenv("MAX_MESSAGES","20"))

        self.max_sql_retries=int(os.getenv("MAX_SQL_RETRIES","2"))

        self.sql_max_rows = max(1, int(os.getenv("SQL_MAX_ROWS", "100")))
        self.sql_statement_timeout_ms = max(
            1000, int(os.getenv("SQL_STATEMENT_TIMEOUT_MS", "10000"))
        )



    def validate_groq_api(self):
        if not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is missing. "
                "Configure it before using Groq models."
                )


settings = Settings()