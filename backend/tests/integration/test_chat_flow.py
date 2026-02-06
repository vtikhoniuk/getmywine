"""Integration tests for chat message flow.

Tests:
- T029: Send message and receive AI response
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestChatFlow:
    """Integration tests for complete chat flow."""

    async def test_complete_chat_flow(self, client: AsyncClient):
        """T029: Complete flow from registration to chat."""
        # 1. Register user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "chatflow@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        assert register_response.status_code == 201

        # 2. Get conversation (creates with welcome message)
        conv_response = await client.get("/api/v1/chat/conversation")
        assert conv_response.status_code == 200
        assert conv_response.json()["is_new"] is True
        assert len(conv_response.json()["messages"]) == 1

        # 3. Send a message
        msg_response = await client.post(
            "/api/v1/chat/messages",
            json={"content": "Какое вино подходит к стейку?"},
        )
        assert msg_response.status_code == 200

        data = msg_response.json()
        assert data["user_message"]["content"] == "Какое вино подходит к стейку?"
        assert len(data["assistant_message"]["content"]) > 0

        # 4. Get conversation again - should have 3 messages now
        conv_response2 = await client.get("/api/v1/chat/conversation")
        assert conv_response2.status_code == 200
        messages = conv_response2.json()["messages"]
        assert len(messages) == 3  # welcome + user + AI

    async def test_multiple_messages_in_conversation(self, client: AsyncClient):
        """Multiple messages should accumulate in conversation."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "multi@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create conversation
        await client.get("/api/v1/chat/conversation")

        # Send multiple messages
        messages_to_send = [
            "Привет!",
            "Расскажи о красном вине",
            "А что насчёт белого?",
        ]

        for msg in messages_to_send:
            response = await client.post(
                "/api/v1/chat/messages",
                json={"content": msg},
            )
            assert response.status_code == 200

        # Check total messages: 1 welcome + 3 user + 3 AI = 7
        conv_response = await client.get("/api/v1/chat/conversation")
        messages = conv_response.json()["messages"]
        assert len(messages) == 7

    async def test_messages_persist_across_sessions(self, client: AsyncClient):
        """Messages should persist if user logs out and back in."""
        # Register and send message
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "persist@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        await client.get("/api/v1/chat/conversation")
        await client.post(
            "/api/v1/chat/messages",
            json={"content": "Запомни это сообщение"},
        )

        # Logout
        await client.post("/api/v1/auth/logout")

        # Login again
        await client.post(
            "/api/v1/auth/login",
            json={
                "email": "persist@example.com",
                "password": "testpassword123",
            },
        )

        # Check messages still there
        conv_response = await client.get("/api/v1/chat/conversation")
        messages = conv_response.json()["messages"]

        # Should have: welcome + user message + AI response = 3
        assert len(messages) == 3
        assert messages[0]["is_welcome"] is True
        assert messages[1]["content"] == "Запомни это сообщение"

    async def test_chat_page_accessible_for_authenticated(self, client: AsyncClient):
        """Chat page should be accessible for authenticated users."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "chatpage@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Access chat page
        response = await client.get("/chat")
        assert response.status_code == 200
        assert "GetMyWine" in response.text
        assert "18" in response.text  # 18+ warning

    async def test_ai_responds_in_russian(self, client: AsyncClient):
        """AI responses should be in Russian."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "russian@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        await client.get("/api/v1/chat/conversation")

        # Send message
        response = await client.post(
            "/api/v1/chat/messages",
            json={"content": "Порекомендуй вино"},
        )

        ai_content = response.json()["assistant_message"]["content"]

        # Check for Russian characters (Cyrillic)
        has_cyrillic = any("\u0400" <= c <= "\u04FF" for c in ai_content)
        assert has_cyrillic, "AI response should be in Russian"
