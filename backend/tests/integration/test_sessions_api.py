"""Integration tests for Sessions API.

Tests:
- T009: GET /chat/sessions - list sessions
- T010: GET /chat/sessions/{id} - get specific session (read-only)
- T018: POST /chat/sessions - create new session
- T019: GET /chat/sessions/current - get current session
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestListSessions:
    """T009: Integration tests for GET /chat/sessions."""

    async def test_list_sessions_empty(self, client: AsyncClient):
        """New user should have empty session list initially."""
        # Register user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sessions_empty@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # List sessions - should be empty
        response = await client.get("/api/v1/chat/sessions")
        assert response.status_code == 200

        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0
        assert data["has_more"] is False

    async def test_list_sessions_after_conversation(self, client: AsyncClient):
        """Should show session after creating conversation."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sessions_one@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create conversation via legacy endpoint
        await client.get("/api/v1/chat/conversation")

        # List sessions
        response = await client.get("/api/v1/chat/sessions")
        assert response.status_code == 200

        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["total"] == 1
        assert data["sessions"][0]["message_count"] == 1  # welcome message

    async def test_list_sessions_pagination(self, client: AsyncClient):
        """Should support pagination."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "sessions_paginate@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create multiple sessions
        for _ in range(5):
            await client.post("/api/v1/chat/sessions")

        # Get first page
        response = await client.get("/api/v1/chat/sessions?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["total"] == 5
        assert data["has_more"] is True

        # Get second page
        response = await client.get("/api/v1/chat/sessions?limit=2&offset=2")
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["has_more"] is True

        # Get last page
        response = await client.get("/api/v1/chat/sessions?limit=2&offset=4")
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["has_more"] is False

    async def test_list_sessions_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.get("/api/v1/chat/sessions")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestGetSession:
    """T010: Integration tests for GET /chat/sessions/{id}."""

    async def test_get_session_by_id(self, client: AsyncClient):
        """Should return session with messages."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "session_get@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create conversation and get ID
        conv_response = await client.get("/api/v1/chat/conversation")
        session_id = conv_response.json()["id"]

        # Send a message
        await client.post(
            "/api/v1/chat/messages",
            json={"content": "Test message"},
        )

        # Get session by ID
        response = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == session_id
        assert len(data["messages"]) == 3  # welcome + user + assistant
        assert "is_active" in data

    async def test_get_session_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent session."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "session_404@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        response = await client.get(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_get_session_forbidden_other_user(self, client: AsyncClient):
        """Should not access another user's session."""
        # Register first user and create session
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user1_session@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        conv_response = await client.get("/api/v1/chat/conversation")
        session_id = conv_response.json()["id"]

        # Logout
        await client.post("/api/v1/auth/logout")

        # Register second user
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user2_session@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Try to access first user's session
        response = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert response.status_code == 404  # Should appear as not found


@pytest.mark.asyncio
class TestCreateSession:
    """T018: Integration tests for POST /chat/sessions."""

    async def test_create_new_session(self, client: AsyncClient):
        """Should create new session with welcome message."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "create_session@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create session
        response = await client.post("/api/v1/chat/sessions")
        assert response.status_code == 201

        data = response.json()
        assert "id" in data
        assert data["is_active"] is True
        assert len(data["messages"]) == 1
        assert data["messages"][0]["is_welcome"] is True

    async def test_create_session_closes_previous(self, client: AsyncClient):
        """Creating new session should close previous active session."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "close_previous@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create first session
        response1 = await client.post("/api/v1/chat/sessions")
        first_session_id = response1.json()["id"]

        # Create second session
        response2 = await client.post("/api/v1/chat/sessions")
        second_session_id = response2.json()["id"]

        assert first_session_id != second_session_id

        # First session should be closed (not active)
        response = await client.get(f"/api/v1/chat/sessions/{first_session_id}")
        assert response.json()["is_active"] is False

        # Second session should be active
        response = await client.get(f"/api/v1/chat/sessions/{second_session_id}")
        assert response.json()["is_active"] is True

    async def test_create_session_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.post("/api/v1/chat/sessions")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestCurrentSession:
    """T019: Integration tests for GET /chat/sessions/current."""

    async def test_get_current_creates_if_none(self, client: AsyncClient):
        """Should create session if none exists."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "current_create@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Get current session
        response = await client.get("/api/v1/chat/sessions/current")
        assert response.status_code == 200

        data = response.json()
        assert data["is_active"] is True
        assert len(data["messages"]) == 1  # welcome message

    async def test_get_current_returns_existing(self, client: AsyncClient):
        """Should return existing active session."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "current_existing@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create session
        create_response = await client.post("/api/v1/chat/sessions")
        created_id = create_response.json()["id"]

        # Get current session
        response = await client.get("/api/v1/chat/sessions/current")
        assert response.status_code == 200
        assert response.json()["id"] == created_id

    async def test_get_current_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.get("/api/v1/chat/sessions/current")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestDeleteSession:
    """Integration tests for DELETE /chat/sessions/{id}."""

    async def test_delete_session(self, client: AsyncClient):
        """Should delete session."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "delete_session@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create session
        create_response = await client.post("/api/v1/chat/sessions")
        session_id = create_response.json()["id"]

        # Delete session
        response = await client.delete(f"/api/v1/chat/sessions/{session_id}")
        assert response.status_code == 204

        # Verify deleted
        response = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert response.status_code == 404

    async def test_delete_session_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent session."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "delete_404@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        response = await client.delete(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404

    async def test_delete_session_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.delete(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestUpdateSessionTitle:
    """T027: Integration tests for PATCH /chat/sessions/{id}/title."""

    async def test_update_session_title(self, client: AsyncClient):
        """Should update session title."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "update_title@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create session
        create_response = await client.post("/api/v1/chat/sessions")
        session_id = create_response.json()["id"]

        # Update title
        response = await client.patch(
            f"/api/v1/chat/sessions/{session_id}/title",
            json={"title": "Вино к стейку"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Вино к стейку"

        # Verify title persisted
        response = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert response.json()["title"] == "Вино к стейку"

    async def test_update_title_rejects_long_title(self, client: AsyncClient):
        """Should reject title longer than 30 characters."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "title_truncate@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create session
        create_response = await client.post("/api/v1/chat/sessions")
        session_id = create_response.json()["id"]

        # Update with long title - should be rejected
        long_title = "A" * 50
        response = await client.patch(
            f"/api/v1/chat/sessions/{session_id}/title",
            json={"title": long_title},
        )
        assert response.status_code == 422  # Validation error

    async def test_update_title_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent session."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "title_404@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        response = await client.patch(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000/title",
            json={"title": "Test"},
        )
        assert response.status_code == 404

    async def test_update_title_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        response = await client.patch(
            "/api/v1/chat/sessions/00000000-0000-0000-0000-000000000000/title",
            json={"title": "Test"},
        )
        assert response.status_code == 401

    async def test_update_title_validates_empty(self, client: AsyncClient):
        """Should reject empty title."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "title_empty@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create session
        create_response = await client.post("/api/v1/chat/sessions")
        session_id = create_response.json()["id"]

        # Try to update with empty title
        response = await client.patch(
            f"/api/v1/chat/sessions/{session_id}/title",
            json={"title": ""},
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
class TestSessionLifecycle:
    """T042-T050: Integration tests for session lifecycle (SS-012)."""

    async def test_is_active_returns_true_for_recent_session(
        self, client: AsyncClient
    ):
        """T042: Active session should have is_active=True."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "active_recent@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create session
        response = await client.post("/api/v1/chat/sessions")
        assert response.status_code == 201

        data = response.json()
        assert data["is_active"] is True

    async def test_is_active_false_after_close(self, client: AsyncClient):
        """T042: Closed session should have is_active=False."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "active_close@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create first session
        response1 = await client.post("/api/v1/chat/sessions")
        first_id = response1.json()["id"]

        # Create second session (closes first)
        await client.post("/api/v1/chat/sessions")

        # First session should now be inactive
        response = await client.get(f"/api/v1/chat/sessions/{first_id}")
        assert response.json()["is_active"] is False

    async def test_delete_session_cascades_to_messages(self, client: AsyncClient):
        """T050: Deleting session should delete all messages (CASCADE)."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "cascade_delete@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create session
        create_response = await client.post("/api/v1/chat/sessions")
        session_id = create_response.json()["id"]

        # Send messages to create history
        await client.post(
            "/api/v1/chat/messages",
            json={"content": "Test message 1"},
        )
        await client.post(
            "/api/v1/chat/messages",
            json={"content": "Test message 2"},
        )

        # Verify messages exist
        get_response = await client.get(f"/api/v1/chat/sessions/{session_id}")
        # welcome + 2 user + 2 assistant = 5 messages
        assert len(get_response.json()["messages"]) == 5

        # Delete session
        delete_response = await client.delete(f"/api/v1/chat/sessions/{session_id}")
        assert delete_response.status_code == 204

        # Verify session and messages are gone
        get_response = await client.get(f"/api/v1/chat/sessions/{session_id}")
        assert get_response.status_code == 404

    async def test_list_sessions_shows_active_status(self, client: AsyncClient):
        """Session list should include is_active status for each session."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "list_active@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Create two sessions (first gets closed)
        await client.post("/api/v1/chat/sessions")
        await client.post("/api/v1/chat/sessions")

        # List sessions
        response = await client.get("/api/v1/chat/sessions")
        sessions = response.json()["sessions"]

        assert len(sessions) == 2
        # Newest first: one active, one inactive
        active_count = sum(1 for s in sessions if s["is_active"])
        inactive_count = sum(1 for s in sessions if not s["is_active"])
        assert active_count == 1
        assert inactive_count == 1
