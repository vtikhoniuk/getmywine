"""Contract tests for POST /auth/login endpoint."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestLoginContract:
    """Contract tests for login endpoint."""

    async def test_login_success_returns_200(self, client: AsyncClient):
        """Successful login should return 200 with user data."""
        # First register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Clear cookies from registration
        client.cookies.clear()

        # Then login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["email"] == "login@example.com"
        assert "password" not in data
        assert "password_hash" not in data

    async def test_login_sets_cookie(self, client: AsyncClient):
        """Successful login should set access_token cookie."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "cookie-login@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        client.cookies.clear()

        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "cookie-login@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        assert "access_token" in response.cookies

    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        """Wrong password should return 401."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrong-pass@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        client.cookies.clear()

        # Login with wrong password
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrong-pass@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Неверный email или пароль"

    async def test_login_nonexistent_user_returns_401(self, client: AsyncClient):
        """Login with non-existent user should return 401."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 401
        # Same error message to prevent email enumeration
        assert response.json()["detail"] == "Неверный email или пароль"

    async def test_login_invalid_email_returns_422(self, client: AsyncClient):
        """Invalid email format should return 422."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "not-an-email",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 422
