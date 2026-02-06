"""Unit tests for TelegramUserRepository.

T014 [US1]: Tests for TelegramUserRepository per TDD requirement.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram_user import TelegramUser
from app.models.user import User
from app.repositories.telegram_user import TelegramUserRepository


@pytest_asyncio.fixture
async def repo(db_session: AsyncSession) -> TelegramUserRepository:
    """Create repository instance."""
    return TelegramUserRepository(db_session)


@pytest_asyncio.fixture
async def user(db_session: AsyncSession) -> User:
    """Create a test web user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash="hashed",
        is_age_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
class TestCreate:
    """Tests for TelegramUserRepository.create()."""

    async def test_creates_telegram_user(
        self, repo: TelegramUserRepository, db_session: AsyncSession
    ):
        """Should create a new Telegram user."""
        telegram_user = await repo.create(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User",
            language_code="ru",
        )

        assert telegram_user.id is not None
        assert telegram_user.telegram_id == 123456789
        assert telegram_user.username == "testuser"
        assert telegram_user.first_name == "Test"
        assert telegram_user.last_name == "User"
        assert telegram_user.language_code == "ru"
        assert telegram_user.is_age_verified is False
        assert telegram_user.user_id is None

    async def test_creates_with_default_language(
        self, repo: TelegramUserRepository
    ):
        """Should use default language code if not specified."""
        telegram_user = await repo.create(telegram_id=123456789)

        assert telegram_user.language_code == "ru"

    async def test_creates_with_age_verified(
        self, repo: TelegramUserRepository
    ):
        """Should create user with age verification status."""
        telegram_user = await repo.create(
            telegram_id=123456789,
            is_age_verified=True,
        )

        assert telegram_user.is_age_verified is True


@pytest.mark.asyncio
class TestGetByTelegramId:
    """Tests for TelegramUserRepository.get_by_telegram_id()."""

    async def test_returns_user_if_exists(
        self, repo: TelegramUserRepository, db_session: AsyncSession
    ):
        """Should return user if telegram_id exists."""
        # Create a user first
        telegram_user = TelegramUser(
            telegram_id=123456789,
            username="existing",
        )
        db_session.add(telegram_user)
        await db_session.flush()

        # Retrieve
        result = await repo.get_by_telegram_id(123456789)

        assert result is not None
        assert result.telegram_id == 123456789
        assert result.username == "existing"

    async def test_returns_none_if_not_exists(
        self, repo: TelegramUserRepository
    ):
        """Should return None if telegram_id doesn't exist."""
        result = await repo.get_by_telegram_id(999999999)

        assert result is None


@pytest.mark.asyncio
class TestGetOrCreate:
    """Tests for TelegramUserRepository.get_or_create()."""

    async def test_creates_new_user(
        self, repo: TelegramUserRepository
    ):
        """Should create user if doesn't exist."""
        telegram_user, was_created = await repo.get_or_create(
            telegram_id=123456789,
            username="newuser",
            first_name="New",
            language_code="en",
        )

        assert was_created is True
        assert telegram_user.telegram_id == 123456789
        assert telegram_user.username == "newuser"
        assert telegram_user.first_name == "New"
        assert telegram_user.language_code == "en"

    async def test_returns_existing_user(
        self, repo: TelegramUserRepository, db_session: AsyncSession
    ):
        """Should return existing user without creating new one."""
        # Create a user first
        existing = TelegramUser(
            telegram_id=123456789,
            username="existing",
            first_name="Existing",
        )
        db_session.add(existing)
        await db_session.flush()

        # Get or create
        telegram_user, was_created = await repo.get_or_create(
            telegram_id=123456789,
            username="newname",
            first_name="NewName",
        )

        assert was_created is False
        assert telegram_user.id == existing.id
        # Profile should be updated
        assert telegram_user.username == "newname"
        assert telegram_user.first_name == "NewName"


@pytest.mark.asyncio
class TestSetAgeVerified:
    """Tests for TelegramUserRepository.set_age_verified()."""

    async def test_sets_age_verified_true(
        self, repo: TelegramUserRepository, db_session: AsyncSession
    ):
        """Should set is_age_verified to True."""
        telegram_user = TelegramUser(
            telegram_id=123456789,
            is_age_verified=False,
        )
        db_session.add(telegram_user)
        await db_session.flush()

        result = await repo.set_age_verified(telegram_user, True)

        assert result.is_age_verified is True

    async def test_sets_age_verified_false(
        self, repo: TelegramUserRepository, db_session: AsyncSession
    ):
        """Should set is_age_verified to False."""
        telegram_user = TelegramUser(
            telegram_id=123456789,
            is_age_verified=True,
        )
        db_session.add(telegram_user)
        await db_session.flush()

        result = await repo.set_age_verified(telegram_user, False)

        assert result.is_age_verified is False


@pytest.mark.asyncio
class TestLinkToUser:
    """Tests for TelegramUserRepository.link_to_user()."""

    async def test_links_telegram_to_web_user(
        self, repo: TelegramUserRepository, user: User, db_session: AsyncSession
    ):
        """Should link Telegram user to web user account."""
        telegram_user = TelegramUser(
            telegram_id=123456789,
            user_id=None,
        )
        db_session.add(telegram_user)
        await db_session.flush()

        result = await repo.link_to_user(telegram_user, user.id)

        assert result.user_id == user.id
