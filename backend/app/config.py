from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Resolve .env from project root (one level up from backend/)
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://getmywine:changeme@localhost:5432/getmywine"

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
    llm_top_p: float = 0.8
    llm_top_k: int = 20
    llm_presence_penalty: float = 1.0
    # "json_schema" (OpenAI strict) or "json_object" (wider compatibility, e.g. cloud.ru)
    llm_response_format: str = "json_schema"

    # Conversation history
    llm_max_history_messages: int = 10  # How many previous messages to include

    # Agent loop (agentic RAG)
    agent_max_iterations: int = 5  # Max tool call iterations per request
    embedding_model: str = "BAAI/bge-m3"  # Model for query embeddings
    structured_output_max_retries: int = 2  # Retries after initial attempt (3 total)

    # Events API (optional, for real-time events)
    calendarific_api_key: str = ""  # For holiday data
    events_country: str = "RU"

    # Session management
    session_inactivity_minutes: int = 30  # Auto-close session after inactivity
    session_retention_days: int = 90  # Keep sessions for this many days

    # Langfuse (LLM observability)
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_host: str = "http://langfuse-web:3000"
    langfuse_tracing_enabled: bool = True

    # Telegram Bot
    telegram_bot_token: str = ""  # Bot token from @BotFather
    telegram_mode: str = "polling"  # "polling" or "webhook"
    telegram_webhook_url: str = ""  # Required for webhook mode
    enable_telegram_bot: bool = True  # Enable/disable bot
    enable_web: bool = True  # Enable/disable web server
    telegram_session_inactivity_hours: int = 24  # Session timeout for Telegram (hours)
    telegram_wine_photo_height: int = 460  # Target height for wine bottle photos (px)

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
