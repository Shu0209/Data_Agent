import pytest
from data_agent.config import Settings


def test_settings_default_values():
    """Settings should load reasonable defaults for local development."""
    settings = Settings()
    assert settings.DB_port == 5432 or isinstance(settings.DB_port, int)
    assert settings.DB_schema == "public"
    assert settings.max_messages > 0
    assert settings.max_sql_retries >= 1


def test_validate_groq_api_raises_when_key_is_missing():
    """validate_groq_api must raise ValueError when groq_api_key is empty or None."""
    settings = Settings()
    settings.groq_api_key = None
    with pytest.raises(ValueError, match="GROQ_API_KEY is missing"):
        settings.validate_groq_api()

    settings.groq_api_key = ""
    with pytest.raises(ValueError, match="GROQ_API_KEY is missing"):
        settings.validate_groq_api()


def test_validate_groq_api_succeeds_when_key_is_present():
    """validate_groq_api should succeed silently when a key exists."""
    settings = Settings()
    settings.groq_api_key = "gsk_dummy_test_key_12345"
    # Should not raise any error
    settings.validate_groq_api()

