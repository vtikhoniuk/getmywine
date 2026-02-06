"""SQLAlchemy models — import all to register mappers."""

from app.models.user import User  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.wine import Wine  # noqa: F401
from app.models.telegram_user import TelegramUser  # noqa: F401
from app.models.login_attempt import LoginAttempt  # noqa: F401
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
