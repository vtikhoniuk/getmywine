"""Integration tests for user logout flow."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestLogoutFlow:
    """Integration tests for the logout flow."""

    async def test_logout_invalidates_session(self, client: AsyncClient):
        """After logout, user should not be able to access protected routes."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout-flow@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Verify can access /me
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 200

        # Logout
        logout_response = await client.post("/api/v1/auth/logout")
        assert logout_response.status_code == 200

        # Verify cannot access /me
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 401

    async def test_can_login_after_logout(self, client: AsyncClient):
        """User should be able to login again after logout."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "relogin@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Logout
        await client.post("/api/v1/auth/logout")

        # Login again
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "relogin@example.com",
                "password": "testpassword123",
            },
        )

        assert login_response.status_code == 200

        # Verify can access /me
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
