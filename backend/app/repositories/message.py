"""Message repository for database operations."""
import uuid
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message, MessageRole


class MessageRepository:
    """Repository for message database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, message_id: uuid.UUID) -> Optional[Message]:
        """Get message by ID."""
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        conversation_id: uuid.UUID,
        role: MessageRole,
        content: str,
        is_welcome: bool = False,
    ) -> Message:
        """Create a new message."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            is_welcome=is_welcome,
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_history(
        self,
        conversation_id: uuid.UUID,
        limit: int = 50,
        before_id: Optional[uuid.UUID] = None,
    ) -> list[Message]:
        """Get message history for a conversation with pagination."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit + 1)  # Fetch one extra to check if there are more
        )

        if before_id:
            # Get the timestamp of the before_id message
            before_message = await self.get_by_id(before_id)
            if before_message:
                query = query.where(Message.created_at < before_message.created_at)

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        # Reverse to get chronological order
        return list(reversed(messages[:limit]))

    async def count_after(
        self,
        conversation_id: uuid.UUID,
        before_id: Optional[uuid.UUID] = None,
        limit: int = 50,
    ) -> bool:
        """Check if there are more messages before the given ID."""
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(limit + 1)
        )

        if before_id:
            before_message = await self.get_by_id(before_id)
            if before_message:
                query = query.where(Message.created_at < before_message.created_at)

        result = await self.db.execute(query)
        messages = list(result.scalars().all())

        return len(messages) > limit
