"""Chat router for conversation and message endpoints."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.schemas.chat import (
    ConversationResponse,
    MessagePair,
    MessageResponse,
    SendMessageRequest,
)
from app.schemas.conversation import (
    SessionDetail,
    SessionList,
    SessionSummary,
    SessionTitleUpdate,
)
from app.schemas.wine import WineSummary
from app.services.chat import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# =============================================================================
# Session Endpoints (US-018, US-019)
# =============================================================================


@router.get("/sessions", response_model=SessionList)
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    List all sessions for the current user.

    Returns sessions sorted by creation date (newest first).
    Includes pagination support.
    """
    repo = ConversationRepository(db)
    conversations, total = await repo.get_all_by_user_id(
        current_user.id,
        limit=limit,
        offset=offset,
    )

    sessions = [
        SessionSummary(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            is_active=conv.is_active,
            message_count=conv.message_count,
        )
        for conv in conversations
    ]

    return SessionList(
        sessions=sessions,
        has_more=(offset + limit) < total,
        total=total,
    )


@router.get("/sessions/current", response_model=SessionDetail)
async def get_current_session(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get the current active session or create a new one.

    If no active session exists, creates a new session with a welcome message.
    """
    chat_service = ChatService(db)
    conversation, is_new, wines = await chat_service.get_or_create_conversation(
        current_user.id,
    )

    messages = [
        MessageResponse.model_validate(msg)
        for msg in conversation.messages
    ]

    suggested_wines = [
        WineSummary.model_validate(wine)
        for wine in wines
    ]

    return SessionDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_active=conversation.is_active,
        message_count=len(messages),
        messages=messages,
        suggested_wines=suggested_wines,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get a specific session by ID (read-only).

    Returns session details with full message history.
    Old sessions cannot be continued - they are read-only.
    """
    repo = ConversationRepository(db)
    conversation = await repo.get_by_id(session_id, user_id=current_user.id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    messages = [
        MessageResponse.model_validate(msg)
        for msg in conversation.messages
    ]

    return SessionDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_active=conversation.is_active,
        message_count=len(messages),
        messages=messages,
    )


@router.post("/sessions", response_model=SessionDetail, status_code=status.HTTP_201_CREATED)
async def create_session(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new session.

    Closes any existing active session and creates a new one with welcome message.
    """
    chat_service = ChatService(db)
    conversation, wines = await chat_service.create_new_session(
        current_user.id,
    )

    messages = [
        MessageResponse.model_validate(msg)
        for msg in conversation.messages
    ]

    suggested_wines = [
        WineSummary.model_validate(wine)
        for wine in wines
    ]

    return SessionDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_active=conversation.is_active,
        message_count=len(messages),
        messages=messages,
        suggested_wines=suggested_wines,
    )


@router.patch("/sessions/{session_id}/title", response_model=SessionSummary)
async def update_session_title(
    session_id: uuid.UUID,
    data: SessionTitleUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update a session's title.

    Used for manual title updates or auto-generated titles from LLM.
    """
    repo = ConversationRepository(db)
    conversation = await repo.get_by_id(session_id, user_id=current_user.id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Store message count before update (refresh loses relationship loading)
    msg_count = conversation.message_count

    conversation = await repo.update_title(conversation, data.title)
    await db.commit()

    return SessionSummary(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        is_active=conversation.is_active,
        message_count=msg_count,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a specific session.

    Permanently removes the session and all its messages.
    """
    repo = ConversationRepository(db)
    conversation = await repo.get_by_id(session_id, user_id=current_user.id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    await repo.delete(conversation)
    await db.commit()


# =============================================================================
# Legacy Conversation Endpoints (for backwards compatibility)
# =============================================================================


@router.get("/conversation", response_model=ConversationResponse)
async def get_or_create_conversation(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get or create a conversation for the current user.

    For new users, creates a conversation with a welcome message.
    For returning users, returns the existing conversation.

    Note: This endpoint is kept for backwards compatibility.
    New code should use GET /sessions/current instead.
    """
    chat_service = ChatService(db)
    conversation, is_new, _ = await chat_service.get_or_create_conversation(
        current_user.id
    )

    # Convert messages to response format
    messages = [
        MessageResponse.model_validate(msg)
        for msg in conversation.messages
    ]

    return ConversationResponse(
        id=conversation.id,
        messages=messages,
        created_at=conversation.created_at,
        is_new=is_new,
    )


@router.post("/messages", response_model=MessagePair)
async def send_message(
    data: SendMessageRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Send a message and get AI response.

    Saves both the user message and AI response to the conversation history.
    """
    chat_service = ChatService(db)

    user_message, ai_message = await chat_service.send_message(
        current_user.id,
        data.content,
    )

    return MessagePair(
        user_message=MessageResponse.model_validate(user_message),
        assistant_message=MessageResponse.model_validate(ai_message),
    )
