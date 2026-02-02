"""Login attempt repository for rate limiting."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.login_attempt import LoginAttempt


class LoginAttemptRepository:
    """Repository for login attempt operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_attempt(
        self,
        email: str,
        ip_address: str,
        success: bool,
    ) -> LoginAttempt:
        """Record a login attempt."""
        attempt = LoginAttempt(
            email=email.lower(),
            ip_address=ip_address,
            success=success,
        )
        self.db.add(attempt)
        await self.db.flush()
        return attempt

    async def count_failed_attempts(
        self,
        email: str,
        ip_address: str,
        minutes: int = 15,
    ) -> int:
        """Count failed login attempts in the last N minutes."""
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

        result = await self.db.execute(
            select(func.count(LoginAttempt.id)).where(
                LoginAttempt.email == email.lower(),
                LoginAttempt.ip_address == ip_address,
                LoginAttempt.success.is_(False),
                LoginAttempt.created_at >= since,
            )
        )
        return result.scalar() or 0

    async def is_rate_limited(
        self,
        email: str,
        ip_address: str,
        max_attempts: int = 5,
        minutes: int = 15,
    ) -> bool:
        """Check if login is rate limited."""
        count = await self.count_failed_attempts(email, ip_address, minutes)
        return count >= max_attempts

    async def cleanup_old_attempts(self, hours: int = 24) -> int:
        """Delete login attempts older than N hours. Returns count deleted."""
        from sqlalchemy import delete

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = await self.db.execute(
            delete(LoginAttempt).where(LoginAttempt.created_at < cutoff)
        )
        return result.rowcount
