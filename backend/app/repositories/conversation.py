"""Conversation repository for database operations."""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation


class ConversationRepository:
    """Repository for conversation database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """Get conversation by ID."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> Optional[Conversation]:
        """Get conversation by user ID."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: uuid.UUID) -> Conversation:
        """Create a new conversation for a user."""
        conversation = Conversation(user_id=user_id)
        self.db.add(conversation)
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation

    async def update_timestamp(self, conversation: Conversation) -> Conversation:
        """Update conversation's updated_at timestamp."""
        # The onupdate trigger should handle this, but we flush to ensure it's applied
        await self.db.flush()
        await self.db.refresh(conversation)
        return conversation
