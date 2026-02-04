"""Unit tests for ChatService.

Tests:
- T017: create_new_session() creates session and closes previous
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.user import User
from app.services.chat import ChatService


@pytest_asyncio.fixture
async def user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed",
        is_age_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def chat_service(db_session: AsyncSession) -> ChatService:
    """Create ChatService instance."""
    return ChatService(db_session)


@pytest.mark.asyncio
class TestCreateNewSession:
    """T017: Tests for create_new_session()."""

    async def test_creates_new_conversation(
        self, chat_service: ChatService, user: User, db_session: AsyncSession
    ):
        """Should create a new conversation."""
        # Patch sommelier to avoid LLM calls
        with patch.object(
            chat_service.sommelier,
            "generate_welcome_with_suggestions",
            new_callable=AsyncMock,
            return_value={"message": "Welcome!", "wines": []},
        ):
            result = await chat_service.create_new_session(user.id)

        assert result is not None
        assert result.user_id == user.id

    async def test_creates_welcome_message(
        self, chat_service: ChatService, user: User, db_session: AsyncSession
    ):
        """Should create welcome message in new session."""
        with patch.object(
            chat_service.sommelier,
            "generate_welcome_with_suggestions",
            new_callable=AsyncMock,
            return_value={"message": "Welcome!", "wines": []},
        ):
            result = await chat_service.create_new_session(user.id)

        assert len(result.messages) == 1
        assert result.messages[0].role == MessageRole.ASSISTANT
        assert result.messages[0].is_welcome is True

    async def test_closes_existing_active_session(
        self, chat_service: ChatService, user: User, db_session: AsyncSession
    ):
        """Should close any existing active session before creating new one."""
        # Create first session
        with patch.object(
            chat_service.sommelier,
            "generate_welcome_with_suggestions",
            new_callable=AsyncMock,
            return_value={"message": "Welcome!", "wines": []},
        ):
            first_session = await chat_service.create_new_session(user.id)
            first_id = first_session.id

            # Create second session
            second_session = await chat_service.create_new_session(user.id)

        # Refresh first session to get updated state
        await db_session.refresh(first_session)

        assert first_session.closed_at is not None
        assert first_session.is_active is False
        assert second_session.is_active is True
        assert first_id != second_session.id

    async def test_no_previous_session_to_close(
        self, chat_service: ChatService, user: User, db_session: AsyncSession
    ):
        """Should work when there's no previous session."""
        with patch.object(
            chat_service.sommelier,
            "generate_welcome_with_suggestions",
            new_callable=AsyncMock,
            return_value={"message": "Welcome!", "wines": []},
        ):
            result = await chat_service.create_new_session(user.id)

        assert result is not None
        assert result.is_active is True

    async def test_passes_user_name_for_personalization(
        self, chat_service: ChatService, user: User, db_session: AsyncSession
    ):
        """Should pass user_name to welcome message generator."""
        mock_generate = AsyncMock(return_value={"message": "Hi John!", "wines": []})

        with patch.object(
            chat_service.sommelier,
            "generate_welcome_with_suggestions",
            mock_generate,
        ):
            await chat_service.create_new_session(user.id, user_name="John")

        mock_generate.assert_called_once()
        call_kwargs = mock_generate.call_args.kwargs
        assert call_kwargs.get("user_name") == "John"


@pytest.mark.asyncio
class TestGetOrCreateConversation:
    """Tests for get_or_create_conversation()."""

    async def test_returns_existing_active_conversation(
        self, chat_service: ChatService, user: User, db_session: AsyncSession
    ):
        """Should return existing active conversation."""
        # Create a conversation first
        with patch.object(
            chat_service.sommelier,
            "generate_welcome_with_suggestions",
            new_callable=AsyncMock,
            return_value={"message": "Welcome!", "wines": []},
        ):
            first_conv, is_new = await chat_service.get_or_create_conversation(user.id)
            assert is_new is True

            # Call again - should return same conversation
            second_conv, is_new = await chat_service.get_or_create_conversation(
                user.id
            )
            assert is_new is False
            assert first_conv.id == second_conv.id

    async def test_creates_new_if_none_exists(
        self, chat_service: ChatService, user: User, db_session: AsyncSession
    ):
        """Should create new conversation if none exists."""
        with patch.object(
            chat_service.sommelier,
            "generate_welcome_with_suggestions",
            new_callable=AsyncMock,
            return_value={"message": "Welcome!", "wines": []},
        ):
            conv, is_new = await chat_service.get_or_create_conversation(user.id)

        assert is_new is True
        assert conv is not None
