"""Integration tests for full authentication flow with pages."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestFullAuthFlow:
    """Tests for complete auth flow: register -> login -> home page."""

    async def test_register_and_access_home(self, client: AsyncClient):
        """After registration, user can access home page and /me endpoint."""
        # Register
        register_response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "hometest@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )
        assert register_response.status_code == 201

        # Home page loads
        home_response = await client.get("/")
        assert home_response.status_code == 200
        assert "GetMyWine" in home_response.text

        # /me returns user data (what JS calls on home page)
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "hometest@example.com"

    async def test_login_and_access_home(self, client: AsyncClient):
        """After login, user can access home page and /me endpoint."""
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "email": "loginflow@example.com",
                "password": "testpassword123",
                "is_age_verified": True,
            },
        )

        # Logout
        await client.post("/api/v1/auth/logout")

        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "loginflow@example.com",
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200

        # Home page loads
        home_response = await client.get("/")
        assert home_response.status_code == 200
        assert "GetMyWine" in home_response.text

        # /me returns user data
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "loginflow@example.com"

    async def test_unauthenticated_can_view_home_but_not_me(
        self, client: AsyncClient
    ):
        """Unauthenticated user can view home page but /me returns 401."""
        # Home page loads for everyone
        home_response = await client.get("/")
        assert home_response.status_code == 200
        assert "GetMyWine" in home_response.text

        # /me returns 401 for unauthenticated
        me_response = await client.get("/api/v1/auth/me")
        assert me_response.status_code == 401

    async def test_all_auth_pages_accessible(self, client: AsyncClient):
        """All authentication pages should be accessible."""
        pages = ["/", "/register", "/login", "/password-reset"]

        for page in pages:
            response = await client.get(page)
            assert response.status_code == 200, f"Page {page} not accessible"
            assert "GetMyWine" in response.text
