"""Chat router for conversation and message endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ConversationResponse,
    MessagePair,
    MessageResponse,
    SendMessageRequest,
)
from app.services.chat import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.get("/conversation", response_model=ConversationResponse)
async def get_or_create_conversation(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get or create a conversation for the current user.

    For new users, creates a conversation with a welcome message.
    For returning users, returns the existing conversation.
    """
    chat_service = ChatService(db)
    conversation, is_new = await chat_service.get_or_create_conversation(
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
