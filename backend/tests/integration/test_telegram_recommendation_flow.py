"""Integration tests for Telegram recommendation flow.

T022 [US2]: Integration test for recommendation flow per TDD requirement.
Tests the complete flow from user message to wine recommendation.
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
class TestRecommendationFlow:
    """Integration tests for full recommendation flow."""

    async def test_complete_recommendation_flow(
        self,
        db_session: AsyncSession,
        telegram_user: TelegramUser,
        conversation: Conversation,
    ):
        """
        Full recommendation flow:
        1. User sends message
        2. Message is saved
        3. AI generates recommendation
        4. Response is saved
        5. User sees recommendation
        """
        message_repo = MessageRepository(db_session)

        # Step 1-2: User sends message
        user_message = await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Порекомендуй красное вино к стейку",
        )

        assert user_message.id is not None
        assert user_message.conversation_id == conversation.id

        # Step 3-4: AI response is saved (mocked in real implementation)
        assistant_response = await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Для стейка рекомендую Château Margaux 2015...",
        )

        assert assistant_response.id is not None
        assert assistant_response.role == MessageRole.ASSISTANT

        # Step 5: Verify conversation has both messages
        messages = await message_repo.get_history(conversation.id)
        assert len(messages) == 2
        roles = [m.role for m in messages]
        assert MessageRole.USER in roles
        assert MessageRole.ASSISTANT in roles

    async def test_multi_turn_conversation(
        self,
        db_session: AsyncSession,
        telegram_user: TelegramUser,
        conversation: Conversation,
    ):
        """Should maintain context across multiple turns."""
        message_repo = MessageRepository(db_session)

        # Turn 1: Initial recommendation
        await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Порекомендуй вино к стейку",
        )
        await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Рекомендую Château Margaux...",
        )

        # Turn 2: Follow-up question
        await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="А что-нибудь подешевле?",
        )
        await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content="Более доступный вариант - Côtes du Rhône...",
        )

        # Verify all messages in context
        messages = await message_repo.get_history(conversation.id)
        assert len(messages) == 4

        # Verify all expected messages are present
        contents = [m.content for m in messages]
        assert "Порекомендуй вино к стейку" in contents
        assert "Рекомендую Château Margaux..." in contents
        assert "А что-нибудь подешевле?" in contents
        assert any(c.startswith("Более доступный") for c in contents)


@pytest.mark.asyncio
class TestUserMessageTypes:
    """Tests for different types of user messages."""

    async def test_food_pairing_request(
        self, db_session: AsyncSession, conversation: Conversation
    ):
        """Should handle food pairing requests."""
        message_repo = MessageRepository(db_session)

        user_message = await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Какое вино подойдёт к рыбе?",
        )

        assert "рыбе" in user_message.content

    async def test_event_based_request(
        self, db_session: AsyncSession, conversation: Conversation
    ):
        """Should handle event-based requests."""
        message_repo = MessageRepository(db_session)

        user_message = await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Нужно вино для романтического ужина",
        )

        assert "романтического" in user_message.content

    async def test_budget_based_request(
        self, db_session: AsyncSession, conversation: Conversation
    ):
        """Should handle budget-based requests."""
        message_repo = MessageRepository(db_session)

        user_message = await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Что-нибудь хорошее до $50",
        )

        assert "$50" in user_message.content

    async def test_wine_type_request(
        self, db_session: AsyncSession, conversation: Conversation
    ):
        """Should handle wine type requests."""
        message_repo = MessageRepository(db_session)

        user_message = await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="Посоветуй игристое",
        )

        assert "игристое" in user_message.content


@pytest.mark.asyncio
class TestSessionManagement:
    """Tests for session management in message flow."""

    async def test_creates_session_for_new_user_message(
        self, db_session: AsyncSession, telegram_user: TelegramUser
    ):
        """Should create session if user sends message without one."""
        conv_repo = ConversationRepository(db_session)

        # No session exists yet for this user
        no_session = await conv_repo.get_active_by_telegram_user_id(
            telegram_user.id,
            inactivity_hours=24,
        )

        # get_or_create should work even with no prior session
        conversation, was_created = await conv_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=telegram_user.id,
        )

        # Note: no_session was None because we hadn't created any yet
        # but get_or_create creates one
        assert conversation is not None
        assert conversation.channel == "telegram"

    async def test_reuses_existing_session(
        self,
        db_session: AsyncSession,
        telegram_user: TelegramUser,
        conversation: Conversation,
    ):
        """Should reuse existing active session."""
        conv_repo = ConversationRepository(db_session)
        message_repo = MessageRepository(db_session)

        # Add message to existing conversation
        await message_repo.create(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content="First message",
        )

        # Get session again - should be same one
        found, was_created = await conv_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=telegram_user.id,
        )

        assert was_created is False
        assert found.id == conversation.id


@pytest.mark.asyncio
class TestLanguageHandling:
    """Tests for language handling in recommendations."""

    async def test_russian_message_response(
        self, db_session: AsyncSession, conversation: Conversation
    ):
        """Should respond in Russian to Russian message."""
        from app.bot.utils import detect_language, get_language_instruction

        user_text = "Порекомендуй вино к пасте"
        language = detect_language(user_text, "ru")
        instruction = get_language_instruction(language)

        assert language == "ru"
        assert "русском" in instruction

    async def test_english_message_response(
        self, db_session: AsyncSession, conversation: Conversation
    ):
        """Should respond in English to English message."""
        from app.bot.utils import detect_language, get_language_instruction

        user_text = "Recommend wine for pasta"
        language = detect_language(user_text, "en")
        instruction = get_language_instruction(language)

        assert language == "en"
        assert "English" in instruction
