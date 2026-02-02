"""Contract tests for password reset endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestPasswordResetRequestContract:
    """Contract tests for POST /auth/password-reset/request."""

    async def test_request_reset_returns_200(self, client: AsyncClient):
        """Request reset should always return 200 (prevent email enumeration)."""
        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "any@example.com"},
        )

        assert response.status_code == 200
        assert "message" in response.json()

    async def test_request_reset_existing_email(self, client: AsyncClient):
        """Request for existing email should return 200."""
        # Register user first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset-test@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        client.cookies.clear()

        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "reset-test@example.com"},
        )

        assert response.status_code == 200
        # Same message for both cases to prevent enumeration
        assert "message" in response.json()

    async def test_request_reset_invalid_email_returns_422(self, client: AsyncClient):
        """Invalid email format should return 422."""
        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestPasswordResetConfirmContract:
    """Contract tests for POST /auth/password-reset/confirm."""

    async def test_confirm_invalid_token_returns_400(self, client: AsyncClient):
        """Invalid token should return 400."""
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": "invalid-token",
                "new_password": "newpassword123",
            },
        )

        assert response.status_code == 400
        assert "detail" in response.json()

    async def test_confirm_short_password_returns_422(self, client: AsyncClient):
        """Password shorter than 8 characters should return 422."""
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": "some-token",
                "new_password": "short",
            },
        )

        assert response.status_code == 422
