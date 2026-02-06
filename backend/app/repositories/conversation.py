"""Conversation repository for database operations."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation

ChannelType = Literal["web", "telegram"]


class ConversationRepository:
    """Repository for conversation database operations.

    Supports multiple sessions per user with lifecycle management.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(
        self,
        conversation_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Conversation]:
        """Get conversation by ID, optionally filtered by user.

        Args:
            conversation_id: The conversation UUID
            user_id: Optional user UUID to verify ownership

        Returns:
            Conversation if found (and owned by user if specified), else None
        """
        query = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        if user_id is not None:
            query = query.where(Conversation.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Conversation]:
        """Get the most recent active conversation for a user.

        Returns the most recently updated conversation that is still active
        (not closed and updated within 30 minutes).
        """
        threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.closed_at.is_(None),
                Conversation.updated_at > threshold,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def get_all_by_user_id(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Conversation], int]:
        """Get all conversations for a user with pagination.

        Args:
            user_id: The user's UUID
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip

        Returns:
            Tuple of (conversations list, total count)
        """
        # Get total count
        count_result = await self.db.execute(
            select(func.count(Conversation.id)).where(
                Conversation.user_id == user_id
            )
        )
        total = count_result.scalar() or 0

        # Get paginated conversations, newest first
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(Conversation.messages))
        )
        conversations = list(result.scalars().all())

        return conversations, total

    async def get_active_by_user_id(
        self, user_id: uuid.UUID
    ) -> Optional[Conversation]:
        """Get the active (not closed) conversation for a user.

        Returns the most recent conversation that hasn't been explicitly closed.
        Note: This doesn't check the 30-minute inactivity rule.
        """
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.closed_at.is_(None),
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: uuid.UUID,
        title: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation for a user.

        Args:
            user_id: The user's UUID
            title: Optional initial title (usually set later via update_title)

        Returns:
            The newly created conversation
        """
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def close_session(
        self,
        conversation: Conversation,
        closed_at: Optional[datetime] = None,
    ) -> Conversation:
        """Close a session by setting closed_at timestamp.

        Args:
            conversation: The conversation to close
            closed_at: Optional specific close time (defaults to now)

        Returns:
            The updated conversation
        """
        conversation.closed_at = closed_at or datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def close_inactive_sessions(
        self,
        user_id: uuid.UUID,
        inactivity_minutes: int = 30,
    ) -> int:
        """Close all inactive sessions for a user.

        Args:
            user_id: The user's UUID
            inactivity_minutes: Minutes of inactivity before closing

        Returns:
            Number of sessions closed
        """
        threshold = datetime.now(timezone.utc) - timedelta(minutes=inactivity_minutes)
        result = await self.db.execute(
            update(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.closed_at.is_(None),
                Conversation.updated_at < threshold,
            )
            .values(closed_at=func.now())
        )
        await self.db.flush()
        return result.rowcount

    async def update_title(
        self,
        conversation: Conversation,
        title: str,
    ) -> Conversation:
        """Update the title of a conversation.

        Args:
            conversation: The conversation to update
            title: The new title (max 30 chars, enforced by model)

        Returns:
            The updated conversation
        """
        conversation.title = title[:30]  # Ensure max length
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def update_timestamp(self, conversation: Conversation) -> Conversation:
        """Update conversation's updated_at timestamp."""
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def delete(self, conversation: Conversation) -> None:
        """Delete a conversation and all its messages.

        Messages are deleted via CASCADE.
        """
        await self.db.delete(conversation)
        await self.db.flush()

    # =========================================================================
    # Telegram channel support
    # =========================================================================

    async def get_active_by_telegram_user_id(
        self,
        telegram_user_id: uuid.UUID,
        inactivity_hours: int = 24,
    ) -> Optional[Conversation]:
        """Get the most recent active conversation for a Telegram user.

        Args:
            telegram_user_id: The TelegramUser's internal UUID
            inactivity_hours: Hours of inactivity before session expires

        Returns:
            Active conversation if found, else None
        """
        threshold = datetime.now(timezone.utc) - timedelta(hours=inactivity_hours)
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.telegram_user_id == telegram_user_id,
                Conversation.channel == "telegram",
                Conversation.closed_at.is_(None),
                Conversation.updated_at > threshold,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def create_telegram_conversation(
        self,
        telegram_user_id: uuid.UUID,
        title: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation for a Telegram user.

        Args:
            telegram_user_id: The TelegramUser's internal UUID
            title: Optional initial title

        Returns:
            The newly created conversation
        """
        conversation = Conversation(
            telegram_user_id=telegram_user_id,
            channel="telegram",
            title=title,
        )
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def close_inactive_telegram_sessions(
        self,
        telegram_user_id: uuid.UUID,
        inactivity_hours: int = 24,
    ) -> int:
        """Close all inactive Telegram sessions for a user.

        Args:
            telegram_user_id: The TelegramUser's internal UUID
            inactivity_hours: Hours of inactivity before closing

        Returns:
            Number of sessions closed
        """
        threshold = datetime.now(timezone.utc) - timedelta(hours=inactivity_hours)
        result = await self.db.execute(
            update(Conversation)
            .where(
                Conversation.telegram_user_id == telegram_user_id,
                Conversation.channel == "telegram",
                Conversation.closed_at.is_(None),
                Conversation.updated_at < threshold,
            )
            .values(closed_at=func.now())
        )
        await self.db.flush()
        return result.rowcount

    async def get_or_create_active_telegram_conversation(
        self,
        telegram_user_id: uuid.UUID,
        inactivity_hours: int = 24,
        title: Optional[str] = None,
    ) -> tuple[Conversation, bool]:
        """Get active Telegram conversation or create a new one.

        Args:
            telegram_user_id: The TelegramUser's internal UUID
            inactivity_hours: Hours of inactivity before session expires
            title: Title for new conversation if created

        Returns:
            Tuple of (Conversation, was_created)
        """
        # Try to get active conversation
        conversation = await self.get_active_by_telegram_user_id(
            telegram_user_id, inactivity_hours
        )
        if conversation:
            return conversation, False

        # Close any expired sessions
        await self.close_inactive_telegram_sessions(
            telegram_user_id, inactivity_hours
        )

        # Create new conversation
        conversation = await self.create_telegram_conversation(
            telegram_user_id, title
        )
        return conversation, True
