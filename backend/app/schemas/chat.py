"""Pydantic schemas for chat functionality."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.message import MessageRole


class SendMessageRequest(BaseModel):
    """Request schema for sending a message."""

    content: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    """Response schema for a single message."""

    id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime
    is_welcome: bool = False

    model_config = {"from_attributes": True}


class MessagePair(BaseModel):
    """Response schema for user message and AI response pair."""

    user_message: MessageResponse
    assistant_message: MessageResponse


class ConversationResponse(BaseModel):
    """Response schema for conversation with message history."""

    id: uuid.UUID
    messages: list[MessageResponse]
    created_at: datetime
    is_new: bool = False

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    """Response schema for paginated message list."""

    messages: list[MessageResponse]
    has_more: bool
