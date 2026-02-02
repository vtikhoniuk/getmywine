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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
