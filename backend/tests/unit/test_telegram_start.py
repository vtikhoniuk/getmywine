"""Unit tests for Telegram /start handler.

T013 [US1]: Tests for start handler per TDD requirement.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_user import TelegramUser
from app.models.conversation import Conversation
from app.repositories.telegram_user import TelegramUserRepository
from app.repositories.conversation import ConversationRepository


def create_mock_update(
    telegram_id: int = 123456789,
    username: str = "testuser",
    first_name: str = "Test",
    last_name: str = "User",
    language_code: str = "ru",
) -> MagicMock:
    """Create a mock Telegram Update object."""
    mock_user = MagicMock()
    mock_user.id = telegram_id
    mock_user.username = username
    mock_user.first_name = first_name
    mock_user.last_name = last_name
    mock_user.language_code = language_code

    mock_message = MagicMock()
    mock_message.from_user = mock_user
    mock_message.reply_text = AsyncMock()

    mock_update = MagicMock()
    mock_update.effective_user = mock_user
    mock_update.message = mock_message

    return mock_update


def create_mock_context() -> MagicMock:
    """Create a mock Telegram Context object."""
    mock_context = MagicMock()
    mock_context.bot = MagicMock()
    return mock_context


@pytest.mark.asyncio
class TestStartHandlerIntegration:
    """Integration-like tests for /start handler with repository."""

    async def test_creates_new_telegram_user(
        self, db_session: AsyncSession
    ):
        """Should create new TelegramUser on first /start."""
        repo = TelegramUserRepository(db_session)

        # Simulate what the handler would do
        telegram_user, was_created = await repo.get_or_create(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            language_code="ru",
        )

        assert was_created is True
        assert telegram_user.telegram_id == 123456789
        assert telegram_user.is_age_verified is False

    async def test_sets_age_verified_on_start(
        self, db_session: AsyncSession
    ):
        """Should set is_age_verified=True when user sends /start."""
        repo = TelegramUserRepository(db_session)

        # Create user
        telegram_user, _ = await repo.get_or_create(
            telegram_id=123456789,
            username="testuser",
        )
        assert telegram_user.is_age_verified is False

        # Simulate /start setting age verification
        await repo.set_age_verified(telegram_user, True)

        # Verify
        updated = await repo.get_by_telegram_id(123456789)
        assert updated.is_age_verified is True

    async def test_creates_telegram_conversation(
        self, db_session: AsyncSession
    ):
        """Should create new conversation with channel='telegram'."""
        tg_repo = TelegramUserRepository(db_session)
        conv_repo = ConversationRepository(db_session)

        # Create telegram user
        telegram_user, _ = await tg_repo.get_or_create(
            telegram_id=123456789,
            username="testuser",
        )

        # Create telegram conversation
        conversation = await conv_repo.create_telegram_conversation(
            telegram_user_id=telegram_user.id,
            title="Новый диалог",
        )

        assert conversation.channel == "telegram"
        assert conversation.telegram_user_id == telegram_user.id
        assert conversation.user_id is None  # No web user link

    async def test_returns_existing_user_on_repeat_start(
        self, db_session: AsyncSession
    ):
        """Should return existing user if they send /start again."""
        repo = TelegramUserRepository(db_session)

        # First start
        user1, created1 = await repo.get_or_create(
            telegram_id=123456789,
            username="testuser",
        )
        await repo.set_age_verified(user1, True)

        # Second start (different username - user updated profile)
        user2, created2 = await repo.get_or_create(
            telegram_id=123456789,
            username="newusername",
        )

        assert created1 is True
        assert created2 is False
        assert user1.id == user2.id
        # Username should be updated
        assert user2.username == "newusername"
        # Age verified should persist
        assert user2.is_age_verified is True


@pytest.mark.asyncio
class TestStartHandlerBehavior:
    """Tests for start handler expected behavior (design validation)."""

    async def test_start_creates_user_and_session(
        self, db_session: AsyncSession
    ):
        """Full /start flow: create user, verify age, create session."""
        tg_repo = TelegramUserRepository(db_session)
        conv_repo = ConversationRepository(db_session)

        # 1. Get or create telegram user
        telegram_user, was_new = await tg_repo.get_or_create(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            language_code="ru",
        )

        # 2. Mark age verified (implicit by using bot)
        await tg_repo.set_age_verified(telegram_user, True)

        # 3. Get or create active conversation
        conversation, conv_created = await conv_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=telegram_user.id,
            inactivity_hours=24,
            title="Новый диалог",
        )

        # Assertions
        assert telegram_user.is_age_verified is True
        assert conversation.channel == "telegram"
        assert conversation.telegram_user_id == telegram_user.id
        assert conv_created is True

    async def test_start_reuses_active_session(
        self, db_session: AsyncSession
    ):
        """Should reuse active session if exists."""
        tg_repo = TelegramUserRepository(db_session)
        conv_repo = ConversationRepository(db_session)

        # Create user and first session
        telegram_user, _ = await tg_repo.get_or_create(telegram_id=123456789)
        conv1, created1 = await conv_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=telegram_user.id,
        )

        # Try to get session again (simulating second /start)
        conv2, created2 = await conv_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=telegram_user.id,
        )

        assert created1 is True
        assert created2 is False
        assert conv1.id == conv2.id


@pytest.mark.asyncio
class TestLanguageDetection:
    """Tests for language detection in /start context."""

    async def test_stores_telegram_language_code(
        self, db_session: AsyncSession
    ):
        """Should store user's Telegram language code."""
        repo = TelegramUserRepository(db_session)

        # Russian locale
        user_ru, _ = await repo.get_or_create(
            telegram_id=111111,
            language_code="ru",
        )
        assert user_ru.language_code == "ru"

        # English locale
        user_en, _ = await repo.get_or_create(
            telegram_id=222222,
            language_code="en",
        )
        assert user_en.language_code == "en"

    async def test_default_language_is_russian(
        self, db_session: AsyncSession
    ):
        """Should default to Russian if no language code."""
        repo = TelegramUserRepository(db_session)

        telegram_user = await repo.create(telegram_id=123456789)

        assert telegram_user.language_code == "ru"
