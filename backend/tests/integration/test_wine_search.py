"""Integration tests for Wine semantic search endpoint."""
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wine import PriceRange, Sweetness, Wine, WineType


@pytest.fixture
async def wines_for_search(db_session: AsyncSession) -> list[Wine]:
    """Create wines for search testing."""
    wines_data = [
        {
            "name": "Steak Companion Red",
            "producer": "Search Test Winery",
            "country": "Argentina",
            "region": "Mendoza",
            "grape_varieties": ["Malbec"],
            "wine_type": WineType.RED,
            "sweetness": Sweetness.DRY,
            "acidity": 3,
            "tannins": 4,
            "body": 5,
            "description": "A bold red wine perfect for grilled steak and red meat dishes.",
            "food_pairings": ["steak", "beef", "lamb"],
            "price_usd": Decimal("55.00"),
            "price_range": PriceRange.MID,
        },
        {
            "name": "Seafood Delight White",
            "producer": "Search Test Winery",
            "country": "France",
            "region": "Loire",
            "grape_varieties": ["Sauvignon Blanc"],
            "wine_type": WineType.WHITE,
            "sweetness": Sweetness.DRY,
            "acidity": 4,
            "tannins": 1,
            "body": 2,
            "description": "Crisp white wine ideal for fish, oysters and light seafood.",
            "food_pairings": ["fish", "oysters", "shrimp"],
            "price_usd": Decimal("35.00"),
            "price_range": PriceRange.MID,
        },
        {
            "name": "Sweet Dessert Wine",
            "producer": "Search Test Winery",
            "country": "Germany",
            "region": "Mosel",
            "grape_varieties": ["Riesling"],
            "wine_type": WineType.WHITE,
            "sweetness": Sweetness.SWEET,
            "acidity": 4,
            "tannins": 1,
            "body": 3,
            "description": "A sweet dessert wine with honey and apricot notes.",
            "food_pairings": ["dessert", "fruit", "cheese"],
            "price_usd": Decimal("45.00"),
            "price_range": PriceRange.MID,
        },
    ]

    wines = []
    for data in wines_data:
        wine = Wine(**data)
        db_session.add(wine)
        wines.append(wine)

    await db_session.commit()
    for wine in wines:
        await db_session.refresh(wine)

    return wines


class TestSemanticSearch:
    """Tests for POST /api/v1/wines/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_returns_results(
        self, async_client: AsyncClient, wines_for_search: list[Wine]
    ):
        """Test that semantic search returns results."""
        response = await async_client.post(
            "/api/v1/wines/search",
            json={"query": "red wine for steak", "limit": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data
        assert data["query"] == "red wine for steak"

    @pytest.mark.asyncio
    async def test_search_with_filters(
        self, async_client: AsyncClient, wines_for_search: list[Wine]
    ):
        """Test semantic search with additional filters."""
        response = await async_client.post(
            "/api/v1/wines/search",
            json={
                "query": "wine for dinner",
                "limit": 5,
                "filters": {"wine_type": "red"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        # If results exist, they should all be red wines
        for result in data["results"]:
            if result["wine"]["wine_type"]:
                assert result["wine"]["wine_type"] == "red"

    @pytest.mark.asyncio
    async def test_search_empty_query_validation(self, async_client: AsyncClient):
        """Test that empty query returns validation error."""
        response = await async_client.post(
            "/api/v1/wines/search",
            json={"query": "ab"},  # Too short
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_respects_limit(
        self, async_client: AsyncClient, wines_for_search: list[Wine]
    ):
        """Test that search respects the limit parameter."""
        response = await async_client.post(
            "/api/v1/wines/search",
            json={"query": "wine", "limit": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 2

    @pytest.mark.asyncio
    async def test_search_results_have_score(
        self, async_client: AsyncClient, wines_for_search: list[Wine]
    ):
        """Test that search results include relevance scores."""
        response = await async_client.post(
            "/api/v1/wines/search",
            json={"query": "seafood wine", "limit": 5},
        )

        assert response.status_code == 200
        data = response.json()
        for result in data["results"]:
            assert "score" in result
            assert "wine" in result


class TestFilterSearch:
    """Tests for GET /api/v1/wines with filters (already in test_wine_api.py but adding more)."""

    @pytest.mark.asyncio
    async def test_filter_by_wine_type(
        self, async_client: AsyncClient, wines_for_search: list[Wine]
    ):
        """Test filtering by wine type."""
        response = await async_client.get("/api/v1/wines?wine_type=red")

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["wine_type"] == "red"

    @pytest.mark.asyncio
    async def test_filter_by_sweetness(
        self, async_client: AsyncClient, wines_for_search: list[Wine]
    ):
        """Test filtering by sweetness."""
        response = await async_client.get("/api/v1/wines?sweetness=dry")

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["sweetness"] == "dry"

    @pytest.mark.asyncio
    async def test_filter_by_price_range(
        self, async_client: AsyncClient, wines_for_search: list[Wine]
    ):
        """Test filtering by price range."""
        response = await async_client.get("/api/v1/wines?price_min=30&price_max=50")

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert 30 <= item["price_usd"] <= 50
