"""Telegram user repository for database operations."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.telegram_user import TelegramUser


class TelegramUserRepository:
    """Repository for Telegram user database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[TelegramUser]:
        """Get Telegram user by internal ID."""
        result = await self.db.execute(
            select(TelegramUser).where(TelegramUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[TelegramUser]:
        """Get Telegram user by Telegram ID."""
        result = await self.db.execute(
            select(TelegramUser).where(TelegramUser.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[TelegramUser]:
        """Get Telegram user by linked web user ID."""
        result = await self.db.execute(
            select(TelegramUser).where(TelegramUser.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "ru",
        is_age_verified: bool = False,
    ) -> TelegramUser:
        """Create a new Telegram user.

        Args:
            telegram_id: Telegram user ID
            username: Telegram username (without @)
            first_name: User's first name
            last_name: User's last name
            language_code: Preferred language code
            is_age_verified: Whether user confirmed age via /start

        Returns:
            The newly created TelegramUser
        """
        telegram_user = TelegramUser(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_age_verified=is_age_verified,
        )
        self.db.add(telegram_user)
        await self.db.flush()
        await self.db.refresh(telegram_user)
        return telegram_user

    async def update(
        self,
        telegram_user: TelegramUser,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None,
    ) -> TelegramUser:
        """Update Telegram user profile.

        Args:
            telegram_user: The TelegramUser to update
            username: New username (if provided)
            first_name: New first name (if provided)
            last_name: New last name (if provided)
            language_code: New language code (if provided)

        Returns:
            The updated TelegramUser
        """
        if username is not None:
            telegram_user.username = username
        if first_name is not None:
            telegram_user.first_name = first_name
        if last_name is not None:
            telegram_user.last_name = last_name
        if language_code is not None:
            telegram_user.language_code = language_code
        await self.db.flush()
        await self.db.refresh(telegram_user)
        return telegram_user

    async def link_to_user(
        self,
        telegram_user: TelegramUser,
        user_id: uuid.UUID,
    ) -> TelegramUser:
        """Link Telegram user to a web user account.

        Args:
            telegram_user: The TelegramUser to link
            user_id: The web User ID to link to

        Returns:
            The updated TelegramUser
        """
        telegram_user.user_id = user_id
        await self.db.flush()
        await self.db.refresh(telegram_user)
        return telegram_user

    async def set_age_verified(
        self,
        telegram_user: TelegramUser,
        is_verified: bool = True,
    ) -> TelegramUser:
        """Set age verification status.

        Args:
            telegram_user: The TelegramUser to update
            is_verified: Verification status

        Returns:
            The updated TelegramUser
        """
        telegram_user.is_age_verified = is_verified
        await self.db.flush()
        await self.db.refresh(telegram_user)
        return telegram_user

    async def get_or_create(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "ru",
    ) -> tuple[TelegramUser, bool]:
        """Get existing Telegram user or create a new one.

        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            first_name: User's first name
            last_name: User's last name
            language_code: Preferred language code

        Returns:
            Tuple of (TelegramUser, was_created)
        """
        existing = await self.get_by_telegram_id(telegram_id)
        if existing:
            # Update profile info if changed
            await self.update(
                existing,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
            )
            return existing, False

        # Create new user
        new_user = await self.create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_age_verified=False,
        )
        return new_user, True
