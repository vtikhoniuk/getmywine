"""Integration tests for Wine API endpoints."""
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wine import PriceRange, Sweetness, Wine, WineType


@pytest.fixture
async def sample_wine_in_db(db_session: AsyncSession) -> Wine:
    """Create a sample wine in the database for API tests."""
    wine = Wine(
        id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        name="API Test Wine",
        producer="API Test Producer",
        vintage_year=2021,
        country="Italy",
        region="Tuscany",
        appellation="Chianti",
        grape_varieties=["Sangiovese"],
        wine_type=WineType.RED,
        sweetness=Sweetness.DRY,
        acidity=4,
        tannins=3,
        body=4,
        description="A test wine for API integration tests.",
        tasting_notes="Cherry, leather, tobacco",
        food_pairings=["pasta", "pizza"],
        price_rub=Decimal("3600.00"),
        price_range=PriceRange.MID,
        image_url="https://example.com/api-wine.jpg",
    )
    db_session.add(wine)
    await db_session.commit()
    await db_session.refresh(wine)
    return wine


class TestGetWineById:
    """Tests for GET /api/v1/wines/{wine_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_wine_by_id_success(
        self, async_client: AsyncClient, sample_wine_in_db: Wine
    ):
        """Test getting a wine by ID returns correct data."""
        response = await async_client.get(
            f"/api/v1/wines/{sample_wine_in_db.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_wine_in_db.id)
        assert data["name"] == "API Test Wine"
        assert data["producer"] == "API Test Producer"
        assert data["wine_type"] == "red"
        assert data["country"] == "Italy"
        assert data["price_rub"] == 3600.0

    @pytest.mark.asyncio
    async def test_get_wine_by_id_not_found(self, async_client: AsyncClient):
        """Test getting non-existent wine returns 404."""
        nonexistent_id = "99999999-9999-9999-9999-999999999999"
        response = await async_client.get(f"/api/v1/wines/{nonexistent_id}")

        assert response.status_code == 404
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_get_wine_by_id_invalid_uuid(self, async_client: AsyncClient):
        """Test getting wine with invalid UUID returns 422."""
        response = await async_client.get("/api/v1/wines/not-a-uuid")

        assert response.status_code == 422


class TestListWines:
    """Tests for GET /api/v1/wines endpoint."""

    @pytest.mark.asyncio
    async def test_list_wines_success(
        self, async_client: AsyncClient, sample_wine_in_db: Wine
    ):
        """Test listing wines returns paginated response."""
        response = await async_client.get("/api/v1/wines")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_list_wines_with_pagination(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test listing wines with custom limit and offset."""
        # Create multiple wines
        for i in range(5):
            wine = Wine(
                name=f"Pagination Wine {i}",
                producer="Producer",
                country="France",
                region="Burgundy",
                grape_varieties=["Pinot Noir"],
                wine_type=WineType.RED,
                sweetness=Sweetness.DRY,
                acidity=3,
                tannins=2,
                body=3,
                description="Wine for pagination testing purposes.",
                price_rub=Decimal("4800.00"),
                price_range=PriceRange.MID,
            )
            db_session.add(wine)
        await db_session.commit()

        response = await async_client.get("/api/v1/wines?limit=2&offset=1")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert data["offset"] == 1
        assert len(data["items"]) <= 2

    @pytest.mark.asyncio
    async def test_list_wines_empty_result(self, async_client: AsyncClient):
        """Test listing wines with high offset returns empty list."""
        response = await async_client.get("/api/v1/wines?offset=10000")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_list_wines_includes_summary_fields(
        self, async_client: AsyncClient, sample_wine_in_db: Wine
    ):
        """Test that wine list items include summary fields."""
        response = await async_client.get("/api/v1/wines")

        assert response.status_code == 200
        data = response.json()
        if data["items"]:
            item = data["items"][0]
            assert "id" in item
            assert "name" in item
            assert "producer" in item
            assert "wine_type" in item
            assert "price_rub" in item
            assert "country" in item
