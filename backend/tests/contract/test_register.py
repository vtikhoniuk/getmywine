"""Contract tests for POST /auth/register endpoint."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegisterContract:
    """Contract tests for registration endpoint."""

    async def test_register_success_returns_201(self, client: AsyncClient):
        """Successful registration should return 201 with user data."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["email"] == "test@example.com"
        assert data["is_age_verified"] is True
        assert "created_at" in data
        # Password should not be in response
        assert "password" not in data
        assert "password_hash" not in data

    async def test_register_sets_cookie(self, client: AsyncClient):
        """Successful registration should set access_token cookie."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "cookie@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        assert response.status_code == 201
        assert "access_token" in response.cookies

    async def test_register_invalid_email_returns_422(self, client: AsyncClient):
        """Invalid email should return 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        assert response.status_code == 422

    async def test_register_short_password_returns_422(self, client: AsyncClient):
        """Password shorter than 8 characters should return 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
                "is_age_verified": True,
            },
        )

        assert response.status_code == 422

    async def test_register_age_not_verified_returns_422(self, client: AsyncClient):
        """Registration without age verification should return 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "testpassword123",
                "is_age_verified": False,
            },
        )

        assert response.status_code == 422

    async def test_register_duplicate_email_returns_400(self, client: AsyncClient):
        """Duplicate email should return 400."""
        # First registration
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Second registration with same email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "anotherpassword123",
                "is_age_verified": True,
            },
        )

        assert response.status_code == 400
        assert "detail" in response.json()

    async def test_register_missing_fields_returns_422(self, client: AsyncClient):
        """Missing required fields should return 422."""
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 422
