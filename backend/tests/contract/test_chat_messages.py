"""Contract tests for POST /chat/messages endpoint.

Tests:
- T019: Success - send message and get AI response
- T020: Validation error - empty or too long message
- T021: Unauthorized user gets 401
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestChatMessagesContract:
    """Contract tests for /chat/messages endpoint."""

    async def test_send_message_returns_pair(self, client: AsyncClient):
        """T019: Sending message returns user message and AI response."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sender@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # First get/create conversation
        await client.get("/api/v1/chat/conversation")

        # Send a message
        response = await client.post(
            "/api/v1/chat/messages",
            json={"content": "Посоветуй вино к стейку"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check MessagePair structure
        assert "user_message" in data
        assert "assistant_message" in data

        # Check user message
        user_msg = data["user_message"]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == "Посоветуй вино к стейку"
        assert "id" in user_msg
        assert "created_at" in user_msg

        # Check AI response
        ai_msg = data["assistant_message"]
        assert ai_msg["role"] == "assistant"
        assert len(ai_msg["content"]) > 0
        assert "id" in ai_msg
        assert "created_at" in ai_msg

    async def test_empty_message_returns_422(self, client: AsyncClient):
        """T020: Empty message should return validation error."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "empty@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        await client.get("/api/v1/chat/conversation")

        response = await client.post(
            "/api/v1/chat/messages",
            json={"content": ""},
        )

        assert response.status_code == 422

    async def test_too_long_message_returns_422(self, client: AsyncClient):
        """T020: Message over 2000 chars should return validation error."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "longmsg@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        await client.get("/api/v1/chat/conversation")

        response = await client.post(
            "/api/v1/chat/messages",
            json={"content": "x" * 2001},
        )

        assert response.status_code == 422

    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        """T021: Unauthenticated request should return 401."""
        response = await client.post(
            "/api/v1/chat/messages",
            json={"content": "Hello"},
        )

        assert response.status_code == 401

    async def test_missing_content_returns_422(self, client: AsyncClient):
        """Missing content field should return validation error."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "missing@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        await client.get("/api/v1/chat/conversation")

        response = await client.post(
            "/api/v1/chat/messages",
            json={},
        )

        assert response.status_code == 422

    async def test_ai_response_is_wine_related(self, client: AsyncClient):
        """AI response should be relevant to wine."""
        # Register and login
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wineq@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        await client.get("/api/v1/chat/conversation")

        # Ask about wine
        response = await client.post(
            "/api/v1/chat/messages",
            json={"content": "Какое вино подходит к рыбе?"},
        )

        assert response.status_code == 200
        ai_content = response.json()["assistant_message"]["content"].lower()

        # AI should mention wine-related terms
        wine_terms = ["вин", "белое", "красное", "сорт", "рекомендую", "подойд"]
        assert any(term in ai_content for term in wine_terms)
