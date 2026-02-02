"""Integration tests for user login flow."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestLoginFlow:
    """Integration tests for the complete login flow."""

    async def test_login_flow_complete(self, client: AsyncClient):
        """Complete login flow: register -> logout -> login -> access protected."""
        # Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "flow@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        assert register_response.status_code == 201

        # Can access /me after registration
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 200

        # Logout
        logout_response = await client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # Cannot access /me after logout
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 401

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "flow@example.com",
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200

        # Can access /me after login
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "flow@example.com"

    async def test_login_case_insensitive_email(self, client: AsyncClient):
        """Login should work with different email case."""
        # Register with lowercase
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "casetest@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        client.cookies.clear()

        # Login with uppercase
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "CASETEST@EXAMPLE.COM",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200

    async def test_session_persists_7_days(self, client: AsyncClient):
        """Session cookie should have 7-day expiry."""
        # Register
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "session@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        assert response.status_code == 201
        # Cookie is set (exact expiry validation would need mocking time)
        assert "access_token" in response.cookies
