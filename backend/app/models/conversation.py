"""Conversation model."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.user import User


class Conversation(Base):
    """Conversation model for chat sessions.

    Supports multiple sessions per user with auto-generated titles
    and lifecycle management (auto-close after inactivity).
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # Removed unique=True to allow multiple sessions per user
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Auto-generated session title (max 30 chars)",
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the session was closed (null if active)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="joined")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    @property
    def is_active(self) -> bool:
        """Check if session is active.

        A session is active if:
        - It has not been explicitly closed (closed_at is None)
        - It was updated within the last 30 minutes
        """
        if self.closed_at is not None:
            return False
        threshold = datetime.now(timezone.utc) - timedelta(minutes=30)
        # Handle timezone-naive updated_at
        if self.updated_at.tzinfo is None:
            updated_at_aware = self.updated_at.replace(tzinfo=timezone.utc)
        else:
            updated_at_aware = self.updated_at
        return updated_at_aware > threshold

    @property
    def message_count(self) -> int:
        """Get the number of messages in this conversation."""
        return len(self.messages) if self.messages else 0

    def __repr__(self) -> str:
        return f"<Conversation {self.id} user={self.user_id} title={self.title!r}>"
