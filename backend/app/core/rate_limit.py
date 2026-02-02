"""Rate limiting configuration."""
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

settings = get_settings()

# Global limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
)
