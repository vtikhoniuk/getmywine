"""Integration tests for Telegram /start flow.

T015 [US1]: Integration test for /start flow per TDD requirement.
Tests the complete flow from /start to receiving welcome message with wines.
"""

import uuid
from datetime import datetime, timedelta, timezone
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
async def telegram_user_repo(db_session: AsyncSession) -> TelegramUserRepository:
    """Create TelegramUserRepository instance."""
    return TelegramUserRepository(db_session)


@pytest_asyncio.fixture
async def conversation_repo(db_session: AsyncSession) -> ConversationRepository:
    """Create ConversationRepository instance."""
    return ConversationRepository(db_session)


@pytest_asyncio.fixture
async def message_repo(db_session: AsyncSession) -> MessageRepository:
    """Create MessageRepository instance."""
    return MessageRepository(db_session)


@pytest.mark.asyncio
class TestStartFlowNewUser:
    """Integration tests for /start flow with new user."""

    async def test_complete_start_flow_creates_user_and_session(
        self,
        telegram_user_repo: TelegramUserRepository,
        conversation_repo: ConversationRepository,
        db_session: AsyncSession,
    ):
        """
        Full /start flow:
        1. User sends /start
        2. TelegramUser is created
        3. is_age_verified is set to True
        4. New conversation is created with channel='telegram'
        """
        telegram_id = 123456789
        username = "newuser"
        first_name = "New"
        language_code = "ru"

        # Step 1: Get or create telegram user
        telegram_user, was_created = await telegram_user_repo.get_or_create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language_code=language_code,
        )

        assert was_created is True
        assert telegram_user.telegram_id == telegram_id
        assert telegram_user.username == username
        assert telegram_user.is_age_verified is False

        # Step 2: Set age verified (implicit by /start per spec)
        await telegram_user_repo.set_age_verified(telegram_user, True)

        # Step 3: Create telegram session
        conversation, conv_created = await conversation_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=telegram_user.id,
            inactivity_hours=24,
        )

        assert conv_created is True
        assert conversation.channel == "telegram"
        assert conversation.telegram_user_id == telegram_user.id
        assert conversation.user_id is None  # Not linked to web user

        # Verify in database
        found_user = await telegram_user_repo.get_by_telegram_id(telegram_id)
        assert found_user.is_age_verified is True

        found_conv = await conversation_repo.get_active_by_telegram_user_id(
            telegram_user.id
        )
        assert found_conv is not None
        assert found_conv.id == conversation.id


@pytest.mark.asyncio
class TestStartFlowExistingUser:
    """Integration tests for /start flow with existing user."""

    async def test_existing_user_with_active_session(
        self,
        telegram_user_repo: TelegramUserRepository,
        conversation_repo: ConversationRepository,
        db_session: AsyncSession,
    ):
        """
        Existing user with active session sends /start:
        1. TelegramUser is retrieved (not created)
        2. Existing active conversation is reused
        """
        # Setup: Create existing user and session
        telegram_user = TelegramUser(
            telegram_id=123456789,
            username="existinguser",
            is_age_verified=True,
        )
        db_session.add(telegram_user)
        await db_session.flush()

        existing_conv = Conversation(
            telegram_user_id=telegram_user.id,
            channel="telegram",
        )
        db_session.add(existing_conv)
        await db_session.flush()

        # Simulate /start
        user, was_created = await telegram_user_repo.get_or_create(
            telegram_id=123456789,
            username="existinguser",
        )

        conversation, conv_created = await conversation_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=user.id,
        )

        # User should not be created
        assert was_created is False
        assert user.id == telegram_user.id

        # Conversation should not be created
        assert conv_created is False
        assert conversation.id == existing_conv.id

    async def test_existing_user_with_expired_session(
        self,
        telegram_user_repo: TelegramUserRepository,
        conversation_repo: ConversationRepository,
        db_session: AsyncSession,
    ):
        """
        Existing user with expired session (24h inactivity) sends /start:
        1. TelegramUser is retrieved
        2. Old session is closed
        3. New session is created
        """
        # Setup: Create existing user with old session
        telegram_user = TelegramUser(
            telegram_id=123456789,
            username="existinguser",
            is_age_verified=True,
        )
        db_session.add(telegram_user)
        await db_session.flush()

        old_conv = Conversation(
            telegram_user_id=telegram_user.id,
            channel="telegram",
        )
        # Make session old (>24h)
        old_conv.updated_at = datetime.now(timezone.utc) - timedelta(hours=25)
        db_session.add(old_conv)
        await db_session.flush()

        # Simulate /start
        user, _ = await telegram_user_repo.get_or_create(
            telegram_id=123456789,
            username="existinguser",
        )

        conversation, conv_created = await conversation_repo.get_or_create_active_telegram_conversation(
            telegram_user_id=user.id,
            inactivity_hours=24,
        )

        # New conversation should be created
        assert conv_created is True
        assert conversation.id != old_conv.id
        assert conversation.channel == "telegram"


@pytest.mark.asyncio
class TestSessionTimeoutDifference:
    """Tests for channel-specific session timeouts."""

    async def test_telegram_session_24h_timeout(
        self,
        conversation_repo: ConversationRepository,
        telegram_user_repo: TelegramUserRepository,
        db_session: AsyncSession,
    ):
        """Telegram sessions should have 24h inactivity timeout."""
        telegram_user = TelegramUser(telegram_id=111111)
        db_session.add(telegram_user)
        await db_session.flush()

        # Create telegram conversation
        conv = Conversation(
            telegram_user_id=telegram_user.id,
            channel="telegram",
        )
        db_session.add(conv)
        await db_session.flush()

        # Session should be active at 23h
        conv.updated_at = datetime.now(timezone.utc) - timedelta(hours=23)
        await db_session.flush()

        active_conv = await conversation_repo.get_active_by_telegram_user_id(
            telegram_user.id,
            inactivity_hours=24,
        )
        assert active_conv is not None

        # Session should be expired at 25h
        conv.updated_at = datetime.now(timezone.utc) - timedelta(hours=25)
        await db_session.flush()

        expired_conv = await conversation_repo.get_active_by_telegram_user_id(
            telegram_user.id,
            inactivity_hours=24,
        )
        assert expired_conv is None

    async def test_telegram_conversation_session_timeout_property(
        self, db_session: AsyncSession
    ):
        """Conversation.session_timeout_minutes should be 24h for telegram."""
        telegram_user = TelegramUser(telegram_id=111111)
        db_session.add(telegram_user)
        await db_session.flush()

        telegram_conv = Conversation(
            telegram_user_id=telegram_user.id,
            channel="telegram",
        )
        db_session.add(telegram_conv)
        await db_session.flush()

        assert telegram_conv.session_timeout_minutes == 24 * 60  # 1440 minutes

        # Web conversation should have 30 min
        from app.models.user import User

        user = User(
            email="test@example.com",
            password_hash="hashed",
            is_age_verified=True,
        )
        db_session.add(user)
        await db_session.flush()

        web_conv = Conversation(
            user_id=user.id,
            channel="web",
        )
        db_session.add(web_conv)
        await db_session.flush()

        assert web_conv.session_timeout_minutes == 30


@pytest.mark.asyncio
class TestUserProfileUpdate:
    """Tests for user profile updates on /start."""

    async def test_updates_user_profile_on_start(
        self,
        telegram_user_repo: TelegramUserRepository,
        db_session: AsyncSession,
    ):
        """
        When user sends /start, their profile should be updated
        with latest Telegram data (username, first_name, etc.).
        """
        # Create initial user
        telegram_user = TelegramUser(
            telegram_id=123456789,
            username="oldusername",
            first_name="Old",
            language_code="en",
        )
        db_session.add(telegram_user)
        await db_session.flush()

        # Simulate /start with updated profile
        user, was_created = await telegram_user_repo.get_or_create(
            telegram_id=123456789,
            username="newusername",
            first_name="New",
            language_code="ru",
        )

        assert was_created is False
        assert user.username == "newusername"
        assert user.first_name == "New"
        assert user.language_code == "ru"
