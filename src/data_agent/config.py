
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")

        self.groq_model_api_base = (
            "https://api.groq.com/openai/v1"
        )

        self.groq_model1 = "openai/gpt-oss-120b"
        self.groq_model2 = "openai/gpt-oss-20b"



        # DB config

        self.DB_host=os.getenv("DB_host")
        self.DB_port=os.getenv("DB_port")
        self.DB_name=os.getenv("DB_name")
        self.DB_user=os.getenv("DB_user")
        self.DB_password=os.getenv("DB_password")

        if not self.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is missing. "
                "Please configure it in your .env file."
            )


settings = Settings()