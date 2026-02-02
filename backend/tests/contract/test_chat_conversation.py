"""Contract tests for GET /chat/conversation endpoint.

Tests:
- T012: New user gets conversation with welcome message
- T013: Unauthorized user gets 401
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestChatConversationContract:
    """Contract tests for /chat/conversation endpoint."""

    async def test_new_user_gets_conversation_with_welcome(self, client: AsyncClient):
        """T012: New user should get conversation with welcome message."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Get or create conversation
        response = await client.get("/api/v1/chat/conversation")

        assert response.status_code == 200
        data = response.json()

        # Check conversation structure
        assert "id" in data
        assert "messages" in data
        assert "created_at" in data
        assert data["is_new"] is True

        # Check welcome message exists
        assert len(data["messages"]) == 1
        welcome_msg = data["messages"][0]
        assert welcome_msg["role"] == "assistant"
        assert welcome_msg["is_welcome"] is True
        assert len(welcome_msg["content"]) > 0

    async def test_returning_user_gets_existing_conversation(self, client: AsyncClient):
        """Returning user should get their existing conversation."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "returning@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # First call - creates conversation
        response1 = await client.get("/api/v1/chat/conversation")
        assert response1.status_code == 200
        conversation_id = response1.json()["id"]

        # Second call - returns same conversation
        response2 = await client.get("/api/v1/chat/conversation")
        assert response2.status_code == 200
        assert response2.json()["id"] == conversation_id
        assert response2.json()["is_new"] is False

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        """T013: Unauthenticated request should return 401."""
        response = await client.get("/api/v1/chat/conversation")

        assert response.status_code == 401

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        """Invalid token should return 401."""
        client.cookies.set("access_token", "invalid.token.here")

        response = await client.get("/api/v1/chat/conversation")

        assert response.status_code == 401

    async def test_conversation_response_schema(self, client: AsyncClient):
        """Response should match ConversationResponse schema."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "schema@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        response = await client.get("/api/v1/chat/conversation")
        data = response.json()

        # Validate required fields from contract
        assert isinstance(data["id"], str)  # UUID as string
        assert isinstance(data["messages"], list)
        assert isinstance(data["created_at"], str)  # ISO datetime
        assert isinstance(data["is_new"], bool)

        # Validate message schema
        for msg in data["messages"]:
            assert "id" in msg
            assert "role" in msg
            assert "content" in msg
            assert "created_at" in msg
            assert "is_welcome" in msg
            assert msg["role"] in ["user", "assistant", "system"]
