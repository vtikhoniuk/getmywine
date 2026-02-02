"""Integration tests for password reset flow."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken
from app.models.user import User


@pytest.mark.asyncio
class TestPasswordResetFlow:
    """Integration tests for the password reset flow."""

    async def test_full_password_reset_flow(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        """Complete password reset flow."""
        original_password = "originalpassword123"
        new_password = "newpassword123"

        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reset-flow@example.com",
                "password": original_password,
                "is_age_verified": True,
            },
        )

        client.cookies.clear()

        # Request password reset
        response = await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "reset-flow@example.com"},
        )
        assert response.status_code == 200

        # Get token from database (in real scenario, this would be from email)
        result = await test_db.execute(
            select(PasswordResetToken)
            .join(User)
            .where(User.email == "reset-flow@example.com")
        )
        reset_token = result.scalar_one()

        # Confirm password reset
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": reset_token.token,
                "new_password": new_password,
            },
        )
        assert response.status_code == 200

        # Login with new password
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "reset-flow@example.com",
                "password": new_password,
            },
        )
        assert response.status_code == 200

        # Old password should not work
        client.cookies.clear()
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "reset-flow@example.com",
                "password": original_password,
            },
        )
        assert response.status_code == 401

    async def test_token_cannot_be_reused(
        self, client: AsyncClient, test_db: AsyncSession
    ):
        """Reset token should be invalidated after use."""
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "reuse-test@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        client.cookies.clear()

        # Request reset
        await client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "reuse-test@example.com"},
        )

        # Get token
        result = await test_db.execute(
            select(PasswordResetToken)
            .join(User)
            .where(User.email == "reuse-test@example.com")
        )
        reset_token = result.scalar_one()

        # Use token
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": reset_token.token,
                "new_password": "firstnewpassword123",
            },
        )
        assert response.status_code == 200

        # Try to use same token again
        response = await client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": reset_token.token,
                "new_password": "secondnewpassword123",
            },
        )
        assert response.status_code == 400
