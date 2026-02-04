"""Unit tests for ConversationRepository.

Tests:
- T008: get_all_by_user_id() returns paginated sessions
"""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.user import User
from app.repositories.conversation import ConversationRepository


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
async def repo(db_session: AsyncSession) -> ConversationRepository:
    """Create repository instance."""
    return ConversationRepository(db_session)


@pytest.mark.asyncio
class TestGetAllByUserId:
    """T008: Tests for get_all_by_user_id()."""

    async def test_returns_empty_for_no_conversations(
        self, repo: ConversationRepository, user: User
    ):
        """Should return empty list if user has no conversations."""
        conversations, total = await repo.get_all_by_user_id(user.id)

        assert conversations == []
        assert total == 0

    async def test_returns_user_conversations(
        self, repo: ConversationRepository, user: User, db_session: AsyncSession
    ):
        """Should return all conversations for user."""
        # Create conversations
        conv1 = Conversation(user_id=user.id, title="First")
        conv2 = Conversation(user_id=user.id, title="Second")
        db_session.add_all([conv1, conv2])
        await db_session.flush()

        conversations, total = await repo.get_all_by_user_id(user.id)

        assert len(conversations) == 2
        assert total == 2

    async def test_does_not_return_other_user_conversations(
        self, repo: ConversationRepository, user: User, db_session: AsyncSession
    ):
        """Should not return conversations belonging to other users."""
        # Create another user
        other_user = User(
            id=uuid.uuid4(),
            email="other@example.com",
            password_hash="hashed",
            is_age_verified=True,
        )
        db_session.add(other_user)
        await db_session.flush()

        # Create conversations for both users
        user_conv = Conversation(user_id=user.id, title="User's conv")
        other_conv = Conversation(user_id=other_user.id, title="Other's conv")
        db_session.add_all([user_conv, other_conv])
        await db_session.flush()

        conversations, total = await repo.get_all_by_user_id(user.id)

        assert len(conversations) == 1
        assert total == 1
        assert conversations[0].title == "User's conv"

    async def test_pagination_limit(
        self, repo: ConversationRepository, user: User, db_session: AsyncSession
    ):
        """Should respect limit parameter."""
        # Create 5 conversations
        for i in range(5):
            conv = Conversation(user_id=user.id, title=f"Conv {i}")
            db_session.add(conv)
        await db_session.flush()

        conversations, total = await repo.get_all_by_user_id(user.id, limit=2)

        assert len(conversations) == 2
        assert total == 5

    async def test_pagination_offset(
        self, repo: ConversationRepository, user: User, db_session: AsyncSession
    ):
        """Should respect offset parameter."""
        # Create 5 conversations
        for i in range(5):
            conv = Conversation(user_id=user.id, title=f"Conv {i}")
            db_session.add(conv)
        await db_session.flush()

        conversations, total = await repo.get_all_by_user_id(
            user.id, limit=2, offset=3
        )

        assert len(conversations) == 2
        assert total == 5

    async def test_orders_by_created_at_desc(
        self, repo: ConversationRepository, user: User, db_session: AsyncSession
    ):
        """Should return newest conversations first."""
        from datetime import datetime, timedelta, timezone

        # Create conversations with explicit timestamps
        now = datetime.now(timezone.utc)

        conv1 = Conversation(user_id=user.id, title="Old")
        conv1.created_at = now - timedelta(hours=1)
        db_session.add(conv1)

        conv2 = Conversation(user_id=user.id, title="New")
        conv2.created_at = now
        db_session.add(conv2)

        await db_session.flush()

        conversations, _ = await repo.get_all_by_user_id(user.id)

        # Newest first
        assert conversations[0].title == "New"
        assert conversations[1].title == "Old"


@pytest.mark.asyncio
class TestCloseSession:
    """Tests for close_session()."""

    async def test_close_session_sets_closed_at(
        self, repo: ConversationRepository, user: User, db_session: AsyncSession
    ):
        """Should set closed_at timestamp."""
        conv = Conversation(user_id=user.id)
        db_session.add(conv)
        await db_session.flush()

        assert conv.closed_at is None

        result = await repo.close_session(conv)

        assert result.closed_at is not None
        assert result.is_active is False


@pytest.mark.asyncio
class TestUpdateTitle:
    """Tests for update_title()."""

    async def test_update_title(
        self, repo: ConversationRepository, user: User, db_session: AsyncSession
    ):
        """Should update conversation title."""
        conv = Conversation(user_id=user.id)
        db_session.add(conv)
        await db_session.flush()

        result = await repo.update_title(conv, "New Title")

        assert result.title == "New Title"

    async def test_truncates_long_title(
        self, repo: ConversationRepository, user: User, db_session: AsyncSession
    ):
        """Should truncate title to 30 characters."""
        conv = Conversation(user_id=user.id)
        db_session.add(conv)
        await db_session.flush()

        long_title = "A" * 50
        result = await repo.update_title(conv, long_title)

        assert len(result.title) == 30
