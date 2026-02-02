"""Password reset token repository."""
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:
    """Repository for password reset token operations."""

    TOKEN_EXPIRY_HOURS = 1

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_token(self, user_id: uuid.UUID) -> str:
        """Create a new password reset token."""
        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Calculate expiry
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.TOKEN_EXPIRY_HOURS)

        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )

        self.db.add(reset_token)
        await self.db.flush()

        return token

    async def get_valid_token(self, token: str) -> Optional[PasswordResetToken]:
        """Get a valid (not used, not expired) token."""
        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token == token,
                PasswordResetToken.is_used.is_(False),
                PasswordResetToken.expires_at > now,
            )
        )

        return result.scalar_one_or_none()

    async def mark_as_used(self, reset_token: PasswordResetToken) -> None:
        """Mark token as used."""
        reset_token.is_used = True
        await self.db.flush()

    async def invalidate_user_tokens(self, user_id: uuid.UUID) -> None:
        """Invalidate all tokens for a user."""
        from sqlalchemy import update

        await self.db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user_id)
            .values(is_used=True)
        )

    async def cleanup_expired_tokens(self) -> int:
        """Delete expired tokens. Returns count deleted."""
        from sqlalchemy import delete

        now = datetime.now(timezone.utc)

        result = await self.db.execute(
            delete(PasswordResetToken).where(
                (PasswordResetToken.expires_at < now) | PasswordResetToken.is_used.is_(True)
            )
        )
        return result.rowcount
