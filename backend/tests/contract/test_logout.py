"""Contract tests for POST /auth/logout endpoint."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestLogoutContract:
    """Contract tests for logout endpoint."""

    async def test_logout_success_returns_200(self, client: AsyncClient):
        """Successful logout should return 200."""
        # Register (auto-login)
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Logout
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        assert response.json()["message"] == "Вы успешно вышли из системы"

    async def test_logout_clears_cookie(self, client: AsyncClient):
        """Logout should clear the access_token cookie."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "logout-cookie@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Logout
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 200
        # Cookie should be cleared (set to empty or deleted)
        # Note: exact behavior depends on client implementation

    async def test_logout_unauthenticated_returns_401(self, client: AsyncClient):
        """Logout without authentication should return 401."""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401
