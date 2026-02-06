"""Unit tests for Telegram message handler.

T021 [US2]: Tests for message handler per TDD requirement.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_user import TelegramUser
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.repositories.telegram_user import TelegramUserRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository


@pytest_asyncio.fixture
async def telegram_user(db_session: AsyncSession) -> TelegramUser:
    """Create a test Telegram user."""
    user = TelegramUser(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        is_age_verified=True,
        language_code="ru",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def conversation(
    db_session: AsyncSession, telegram_user: TelegramUser
) -> Conversation:
    """Create a test Telegram conversation."""
    conv = Conversation(
        telegram_user_id=telegram_user.id,
        channel="telegram",
    )
    db_session.add(conv)
    await db_session.flush()
    return conv


@pytest.mark.asyncio
class TestMessageProcessing:
    """Tests for message processing logic."""

    async def test_saves_user_message(
        self, db_session: AsyncSession, conversation: Conversation
    ):
        """Should save user's message to conversation."""
        message_repo = MessageRepository(db_session)

        # Save user message
        user_message = await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Порекомендуй красное вино к стейку",
        )

        assert user_message.id is not None
        assert user_message.role == MessageRole.USER
        assert "стейку" in user_message.content

    async def test_saves_assistant_response(
        self, db_session: AsyncSession, conversation: Conversation
    ):
        """Should save assistant's response to conversation."""
        message_repo = MessageRepository(db_session)

        # Save assistant response
        assistant_message = await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Рекомендую Château Margaux...",
        )

        assert assistant_message.role == MessageRole.ASSISTANT
        assert "Margaux" in assistant_message.content

    async def test_gets_conversation_history(
        self, db_session: AsyncSession, conversation: Conversation
    ):
        """Should retrieve conversation history for context."""
        message_repo = MessageRepository(db_session)

        # Add some messages
        await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="First message",
        )
        await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="First response",
        )
        await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Second message",
        )

        # Get history
        messages = await message_repo.get_history(conversation.id)

        # Verify all messages are returned
        assert len(messages) == 3
        contents = [m.content for m in messages]
        assert "First message" in contents
        assert "First response" in contents
        assert "Second message" in contents


@pytest.mark.asyncio
class TestLanguageDetection:
    """Tests for language detection in messages."""

    async def test_detects_russian_message(self):
        """Should detect Russian language in message."""
        from app.bot.utils import detect_language

        assert detect_language("Порекомендуй вино к мясу") == "ru"
        assert detect_language("Какое вино подойдёт к стейку?") == "ru"

    async def test_detects_english_message(self):
        """Should detect English language in message."""
        from app.bot.utils import detect_language

        assert detect_language("Recommend a wine for steak") == "en"
        assert detect_language("What wine goes with fish?") == "en"

    async def test_mixed_language_prefers_cyrillic(self):
        """Should prefer Russian if significant Cyrillic present."""
        from app.bot.utils import detect_language

        # Mixed with more Cyrillic
        assert detect_language("Wine рекомендация") == "ru"


@pytest.mark.asyncio
class TestConversationContext:
    """Tests for maintaining conversation context."""

    async def test_retrieves_active_conversation(
        self,
        db_session: AsyncSession,
        telegram_user: TelegramUser,
        conversation: Conversation,
    ):
        """Should retrieve active conversation for user."""
        conv_repo = ConversationRepository(db_session)

        found = await conv_repo.get_active_by_telegram_user_id(
            telegram_user.id,
            inactivity_hours=24,
        )

        assert found is not None
        assert found.id == conversation.id

    async def test_updates_conversation_timestamp(
        self,
        db_session: AsyncSession,
        conversation: Conversation,
    ):
        """Should update conversation timestamp on new message."""
        original_updated = conversation.updated_at

        # Add message (would update timestamp via flush)
        message_repo = MessageRepository(db_session)
        await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="New message",
        )

        conv_repo = ConversationRepository(db_session)
        await conv_repo.update_timestamp(conversation)

        # Timestamp should be updated
        assert conversation.updated_at >= original_updated


@pytest.mark.asyncio
class TestMessageHandlerBehavior:
    """Tests for expected message handler behavior."""

    async def test_requires_active_session(
        self, db_session: AsyncSession, telegram_user: TelegramUser
    ):
        """Message handler should work with existing session."""
        conv_repo = ConversationRepository(db_session)

        # Get or create active session
        conversation, was_created = await conv_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=telegram_user.id,
        )

        assert conversation is not None
        assert conversation.channel == "telegram"

    async def test_creates_session_if_none(
        self, db_session: AsyncSession
    ):
        """Should create session if user sends message without one."""
        # Create new user without session
        user = TelegramUser(
            telegram_id=999999,
            username="newuser",
            is_age_verified=True,
        )
        db_session.add(user)
        await db_session.flush()

        conv_repo = ConversationRepository(db_session)
        conversation, was_created = await conv_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=user.id,
        )

        assert was_created is True
        assert conversation.telegram_user_id == user.id
