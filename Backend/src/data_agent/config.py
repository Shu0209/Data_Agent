
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

        self.groq_model_api_base = (
            "https://api.groq.com/openai/v1"
        )

        self.groq_model1 = "openai/gpt-oss-120b"
        self.groq_model2 = "openai/gpt-oss-20b"
        self.groq_guardrail_model="qwen/qwen3.8-27b"



        # DB config

        self.DB_host = os.getenv("DB_host") or os.getenv("DB_HOST") or "localhost"
        self.DB_port = os.getenv("DB_port") or os.getenv("DB_PORT") or 5432
        self.DB_name = os.getenv("DB_name") or os.getenv("DB_NAME") or "data_agent_db"
        self.DB_user = os.getenv("DB_user") or os.getenv("DB_USER") or "postgres"
        self.DB_password = os.getenv("DB_password") or os.getenv("DB_PASSWORD") or "password"

        self.DB_schema = os.getenv("DB_schema") or os.getenv("DB_SCHEMA") or "public"


        # Schema context (what gets sent to the SQL-generation prompt)
        self.schema_cache_ttl = int(os.getenv("SCHEMA_CACHE_TTL_SECONDS", "300"))
        self.schema_max_chars = int(os.getenv("SCHEMA_MAX_CHARS", "12000"))  # ~3k tokens
        self.schema_value_hints = os.getenv("SCHEMA_VALUE_HINTS", "true").lower() in ("1", "true", "yes")
        self.schema_hint_max_values = int(os.getenv("SCHEMA_HINT_MAX_VALUES", "12"))




        if not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is missing. "
                "Please configure it in your .env file."
            )


settings = Settings()