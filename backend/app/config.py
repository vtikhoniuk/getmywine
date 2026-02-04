from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://ai_sommelier:changeme@localhost:5432/ai_sommelier"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    # Rate limiting
    rate_limit_login: str = "5/15minutes"
    rate_limit_register: str = "3/hour"
    rate_limit_password_reset: str = "3/hour"
    rate_limit_enabled: bool = True

    # Cookies
    cookie_secure: bool = True  # Set to False in tests

    # LLM Configuration
    # Provider: "openrouter" (recommended), "anthropic", or "openai"
    llm_provider: str = "openrouter"

    # OpenRouter (uses OpenAI-compatible API)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Direct API keys (if not using OpenRouter)
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Model settings
    # OpenRouter models: "anthropic/claude-sonnet-4", "openai/gpt-4o", etc.
    # Direct: "claude-sonnet-4-20250514", "gpt-4o"
    llm_model: str = "anthropic/claude-sonnet-4"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000

    # Conversation history
    llm_max_history_messages: int = 10  # How many previous messages to include

    # Events API (optional, for real-time events)
    calendarific_api_key: str = ""  # For holiday data
    events_country: str = "RU"

    # Session management
    session_inactivity_minutes: int = 30  # Auto-close session after inactivity
    session_retention_days: int = 90  # Keep sessions for this many days

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
