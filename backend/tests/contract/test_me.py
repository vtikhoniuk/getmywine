"""Contract tests for GET /auth/me endpoint."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestMeContract:
    """Contract tests for /auth/me endpoint."""

    async def test_me_authenticated_returns_200(self, client: AsyncClient):
        """Authenticated user should get their data."""
        # Register (auto-login)
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "me@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Get current user
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@example.com"
        assert "id" in data
        assert "password" not in data
        assert "password_hash" not in data

    async def test_me_unauthenticated_returns_401(self, client: AsyncClient):
        """Unauthenticated request should return 401."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    async def test_me_invalid_token_returns_401(self, client: AsyncClient):
        """Invalid token should return 401."""
        client.cookies.set("access_token", "invalid.token.here")

        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401
