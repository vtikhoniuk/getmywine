"""Integration tests for first visit welcome message.

Tests:
- T018: First visit shows welcome message
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestChatWelcome:
    """Integration tests for chat welcome functionality."""

    async def test_first_visit_shows_welcome_message(self, client: AsyncClient):
        """T018: New user's first visit to chat shows welcome message."""
        # Register user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "firstvisit@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # First visit to chat
        response = await client.get("/api/v1/chat/conversation")

        assert response.status_code == 200
        data = response.json()

        # Should be a new conversation
        assert data["is_new"] is True

        # Should have welcome message
        assert len(data["messages"]) == 1
        welcome = data["messages"][0]
        assert welcome["role"] == "assistant"
        assert welcome["is_welcome"] is True
        assert "AI-сомелье" in welcome["content"]
        assert "вино" in welcome["content"].lower()

    async def test_welcome_message_shown_only_once(self, client: AsyncClient):
        """Welcome message should only appear on first visit."""
        # Register user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "multiplevisits@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # First visit
        response1 = await client.get("/api/v1/chat/conversation")
        assert response1.json()["is_new"] is True
        assert len(response1.json()["messages"]) == 1

        # Second visit
        response2 = await client.get("/api/v1/chat/conversation")
        assert response2.json()["is_new"] is False
        # Still only one message (the welcome message)
        assert len(response2.json()["messages"]) == 1

        # Same conversation
        assert response1.json()["id"] == response2.json()["id"]

    async def test_each_user_gets_own_conversation(self, client: AsyncClient):
        """Each user should have their own separate conversation."""
        # Register first user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user1@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        response1 = await client.get("/api/v1/chat/conversation")
        conv1_id = response1.json()["id"]

        # Logout
        await client.post("/api/v1/auth/logout")

        # Register second user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user2@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        response2 = await client.get("/api/v1/chat/conversation")
        conv2_id = response2.json()["id"]

        # Different conversations
        assert conv1_id != conv2_id

    async def test_complete_registration_to_chat_flow(self, client: AsyncClient):
        """Test the complete flow from registration to seeing welcome."""
        # User registers
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newbie@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        assert register_response.status_code == 201

        # User visits chat (should get welcome)
        chat_response = await client.get("/api/v1/chat/conversation")
        assert chat_response.status_code == 200

        data = chat_response.json()
        assert data["is_new"] is True
        assert len(data["messages"]) == 1

        welcome = data["messages"][0]
        assert welcome["is_welcome"] is True
        # Welcome message explains capabilities
        assert "Подобрать вино" in welcome["content"] or "рекомендовать" in welcome["content"].lower()
