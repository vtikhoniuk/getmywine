"""Authentication service."""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user import UserRepository
from app.core.security import (
    create_access_token,
    verify_password_with_timing_protection,
)
from app.schemas.auth import RegisterRequest, LoginRequest

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def register(self, data: RegisterRequest) -> tuple[User, str]:
        """
        Register a new user.

        Returns:
            Tuple of (user, access_token)

        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        if await self.user_repo.email_exists(data.email):
            logger.warning("Registration failed: email already exists: %s", data.email)
            raise ValueError("Email уже используется")

        # Create user
        user = await self.user_repo.create_user(
            email=data.email,
            password=data.password,
            is_age_verified=data.is_age_verified,
        )
        logger.info("User registered successfully: %s", user.id)

        # Create access token
        access_token = create_access_token(subject=str(user.id))

        return user, access_token

    async def authenticate(
        self, data: LoginRequest
    ) -> Optional[tuple[User, str]]:
        """
        Authenticate user with email and password.

        Returns:
            Tuple of (user, access_token) if successful, None otherwise
        """
        # Get user by email
        user = await self.user_repo.get_by_email(data.email)

        # Verify password with timing protection
        password_hash = user.password_hash if user else None
        if not verify_password_with_timing_protection(data.password, password_hash):
            logger.warning("Authentication failed: invalid credentials for email: %s", data.email)
            return None

        # Check if user is active
        if not user.is_active:
            logger.warning("Authentication failed: user inactive: %s", user.id)
            return None

        # Create access token
        access_token = create_access_token(subject=str(user.id))
        logger.info("User authenticated successfully: %s", user.id)

        return user, access_token

    async def request_password_reset(self, email: str) -> Optional[str]:
        """
        Request password reset.

        Returns:
            Reset token if user exists, None otherwise
        """
        # Import here to avoid circular imports
        from app.repositories.password_reset import PasswordResetTokenRepository

        user = await self.user_repo.get_by_email(email)
        if user is None:
            logger.info("Password reset requested for non-existent email: %s", email)
            return None

        # Create reset token
        reset_repo = PasswordResetTokenRepository(self.db)
        token = await reset_repo.create_token(user.id)
        logger.info("Password reset token created for user: %s", user.id)

        return token

    async def confirm_password_reset(
        self, token: str, new_password: str
    ) -> bool:
        """
        Confirm password reset with token.

        Returns:
            True if successful, False otherwise
        """
        from app.repositories.password_reset import PasswordResetTokenRepository

        reset_repo = PasswordResetTokenRepository(self.db)
        reset_token = await reset_repo.get_valid_token(token)

        if reset_token is None:
            logger.warning("Password reset failed: invalid or expired token")
            return False

        # Get user
        user = await self.user_repo.get_by_id(reset_token.user_id)
        if user is None:
            logger.warning("Password reset failed: user not found for token")
            return False

        # Update password
        await self.user_repo.update_password(user, new_password)

        # Mark token as used
        await reset_repo.mark_as_used(reset_token)
        logger.info("Password reset successful for user: %s", user.id)

        return True
