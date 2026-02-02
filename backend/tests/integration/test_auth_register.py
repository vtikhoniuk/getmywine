"""Integration tests for user registration flow."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import verify_password


@pytest.mark.asyncio
class TestRegistrationFlow:
    """Integration tests for the complete registration flow."""

    async def test_registration_creates_user_in_database(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        """Registration should create user in database."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "dbtest@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        assert response.status_code == 201

        # Verify user in database
        result = await test_db.execute(
            select(User).where(User.email == "dbtest@example.com")
        )
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.email == "dbtest@example.com"
        assert user.is_age_verified is True
        assert user.is_active is True

    async def test_registration_hashes_password(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        """Password should be hashed, not stored in plain text."""
        password = "testpassword123"

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "hashtest@example.com",
                "password": password,
                "is_age_verified": True,
            },
        )

        assert response.status_code == 201

        # Verify password is hashed
        result = await test_db.execute(
            select(User).where(User.email == "hashtest@example.com")
        )
        user = result.scalar_one()

        assert user.password_hash != password
        assert verify_password(password, user.password_hash)

    async def test_registration_email_case_insensitive(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        """Email should be stored in lowercase."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "TestUser@Example.COM",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        assert response.status_code == 201

        # Verify email is lowercase
        result = await test_db.execute(
            select(User).where(User.email == "testuser@example.com")
        )
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.email == "testuser@example.com"

    async def test_registered_user_can_access_protected_route(
        self, client: AsyncClient
    ):
        """After registration, user should be able to access protected routes."""
        # Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "protected@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        assert register_response.status_code == 201

        # Access protected route using cookie
        me_response = await client.get("/api/v1/auth/me")

        assert me_response.status_code == 200
        assert me_response.json()["email"] == "protected@example.com"
