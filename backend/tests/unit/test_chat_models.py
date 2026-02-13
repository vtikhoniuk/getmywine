"""Unit tests for chat models (Conversation, Message, MessageRole)."""
import uuid

import pytest


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_message_role_values(self):
        """MessageRole should have user, assistant, and system values."""
        from app.models.message import MessageRole

        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"

    def test_message_role_is_string_enum(self):
        """MessageRole should be a string enum."""
        from app.models.message import MessageRole

        assert isinstance(MessageRole.USER, str)
        assert MessageRole.USER == "user"

    def test_message_role_count(self):
        """MessageRole should have exactly 3 values."""
        from app.models.message import MessageRole

        assert len(MessageRole) == 3


class TestConversationModel:
    """Tests for Conversation model."""

    def test_conversation_has_required_fields(self):
        """Conversation should have id, user_id, created_at, updated_at fields."""
        from app.models.conversation import Conversation

        # Check model has required columns
        columns = [c.name for c in Conversation.__table__.columns]
        assert "id" in columns
        assert "user_id" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_conversation_user_id_allows_multiple_sessions(self):
        """user_id should NOT be unique to allow multiple sessions per user (EPIC-010)."""
        from app.models.conversation import Conversation

        user_id_column = Conversation.__table__.columns["user_id"]
        # unique=False or None means no unique constraint
        assert user_id_column.unique is not True

    def test_conversation_repr(self):
        """Conversation repr should include id and user_id."""
        from app.models.conversation import Conversation

        conv = Conversation()
        conv.id = uuid.uuid4()
        conv.user_id = uuid.uuid4()

        repr_str = repr(conv)
        assert "Conversation" in repr_str
        assert str(conv.id) in repr_str


class TestMessageModel:
    """Tests for Message model."""

    def test_message_has_required_fields(self):
        """Message should have all required fields."""
        from app.models.message import Message

        columns = [c.name for c in Message.__table__.columns]
        assert "id" in columns
        assert "conversation_id" in columns
        assert "role" in columns
        assert "content" in columns
        assert "created_at" in columns
        assert "is_welcome" in columns

    def test_message_is_welcome_default_false(self):
        """is_welcome should default to False."""
        from app.models.message import Message

        is_welcome_column = Message.__table__.columns["is_welcome"]
        assert is_welcome_column.default.arg is False

    def test_message_repr(self):
        """Message repr should include id and role."""
        from app.models.message import Message, MessageRole

        msg = Message()
        msg.id = uuid.uuid4()
        msg.role = MessageRole.USER

        repr_str = repr(msg)
        assert "Message" in repr_str
        assert "user" in repr_str


class TestChatSchemas:
    """Tests for Pydantic chat schemas."""

    def test_send_message_request_validation(self):
        """SendMessageRequest should validate content length (max 4096 chars)."""
        from app.schemas.chat import SendMessageRequest
        from pydantic import ValidationError

        # Valid message
        msg = SendMessageRequest(content="Hello!")
        assert msg.content == "Hello!"

        # Empty content should fail
        with pytest.raises(ValidationError):
            SendMessageRequest(content="")

        # 4096 chars should succeed (boundary — Telegram parity)
        msg_max = SendMessageRequest(content="x" * 4096)
        assert len(msg_max.content) == 4096

        # Too long content should fail (over 4096 chars)
        with pytest.raises(ValidationError):
            SendMessageRequest(content="x" * 4097)

    def test_message_response_from_attributes(self):
        """MessageResponse should support from_attributes mode."""
        from app.schemas.chat import MessageResponse
        from app.models.message import MessageRole
        from datetime import datetime

        # Create a mock object with attributes
        class MockMessage:
            id = uuid.uuid4()
            role = MessageRole.USER
            content = "Test message"
            created_at = datetime.utcnow()
            is_welcome = False

        response = MessageResponse.model_validate(MockMessage())
        assert response.content == "Test message"
        assert response.role == MessageRole.USER

    def test_conversation_response_includes_messages(self):
        """ConversationResponse should include messages list."""
        from app.schemas.chat import ConversationResponse, MessageResponse
        from app.models.message import MessageRole
        from datetime import datetime

        msg = MessageResponse(
            id=uuid.uuid4(),
            role=MessageRole.ASSISTANT,
            content="Welcome!",
            created_at=datetime.utcnow(),
            is_welcome=True,
        )

        conv = ConversationResponse(
            id=uuid.uuid4(),
            messages=[msg],
            created_at=datetime.utcnow(),
            is_new=True,
        )

        assert len(conv.messages) == 1
        assert conv.is_new is True
