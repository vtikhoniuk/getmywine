"""Pydantic schemas for session/conversation management."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.chat import MessageResponse
from app.schemas.wine import WineSummary


class SessionBase(BaseModel):
    """Base session schema."""

    title: Optional[str] = Field(None, max_length=30)


class SessionCreate(BaseModel):
    """Schema for creating a new session (no fields needed)."""

    pass


class SessionSummary(SessionBase):
    """Session summary for sidebar list."""

    id: uuid.UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    message_count: int

    model_config = {"from_attributes": True}


class SessionDetail(SessionSummary):
    """Full session detail with messages."""

    messages: list[MessageResponse]
    suggested_wines: list[WineSummary] = []

    model_config = {"from_attributes": True}


class SessionList(BaseModel):
    """Paginated list of sessions."""

    sessions: list[SessionSummary]
    has_more: bool
    total: int


class SessionTitleUpdate(BaseModel):
    """Schema for updating session title."""

    title: str = Field(..., min_length=1, max_length=30)
