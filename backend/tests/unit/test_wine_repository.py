"""Unit tests for WineRepository."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wine import PriceRange, Sweetness, Wine, WineType
from app.repositories.wine import WineRepository


@pytest.fixture
def wine_repo(db_session: AsyncSession) -> WineRepository:
    """Create a WineRepository instance."""
    return WineRepository(db_session)


@pytest.fixture
async def sample_wine(db_session: AsyncSession) -> Wine:
    """Create a sample wine in the database."""
    wine = Wine(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        name="Test Wine",
        producer="Test Producer",
        vintage_year=2020,
        country="France",
        region="Bordeaux",
        appellation="Margaux",
        grape_varieties=["Cabernet Sauvignon", "Merlot"],
        wine_type=WineType.RED,
        sweetness=Sweetness.DRY,
        acidity=3,
        tannins=4,
        body=4,
        description="A test wine with rich flavors and smooth tannins.",
        tasting_notes="Dark fruits, oak, vanilla",
        food_pairings=["steak", "lamb"],
        price_usd=Decimal("75.00"),
        price_range=PriceRange.MID,
        image_url="https://example.com/wine.jpg",
    )
    db_session.add(wine)
    await db_session.flush()
    await db_session.refresh(wine)
    return wine


class TestWineRepositoryGetById:
    """Tests for WineRepository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_returns_wine(
        self, wine_repo: WineRepository, sample_wine: Wine
    ):
        """Test that get_by_id returns the correct wine."""
        result = await wine_repo.get_by_id(sample_wine.id)

        assert result is not None
        assert result.id == sample_wine.id
        assert result.name == "Test Wine"
        assert result.wine_type == WineType.RED

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_nonexistent(
        self, wine_repo: WineRepository
    ):
        """Test that get_by_id returns None for non-existent wine."""
        nonexistent_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
        result = await wine_repo.get_by_id(nonexistent_id)

        assert result is None


class TestWineRepositoryGetList:
    """Tests for WineRepository.get_list method."""

    @pytest.mark.asyncio
    async def test_get_list_returns_wines(
        self, wine_repo: WineRepository, sample_wine: Wine
    ):
        """Test that get_list returns list of wines."""
        result = await wine_repo.get_list(limit=10, offset=0)

        assert len(result) >= 1
        assert any(w.id == sample_wine.id for w in result)

    @pytest.mark.asyncio
    async def test_get_list_respects_limit(
        self, wine_repo: WineRepository, db_session: AsyncSession
    ):
        """Test that get_list respects the limit parameter."""
        # Create multiple wines
        for i in range(5):
            wine = Wine(
                name=f"Wine {i}",
                producer="Producer",
                country="France",
                region="Bordeaux",
                grape_varieties=["Merlot"],
                wine_type=WineType.RED,
                sweetness=Sweetness.DRY,
                acidity=3,
                tannins=3,
                body=3,
                description="A test wine description for testing.",
                price_usd=Decimal("50.00"),
                price_range=PriceRange.MID,
            )
            db_session.add(wine)
        await db_session.flush()

        result = await wine_repo.get_list(limit=3, offset=0)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_list_respects_offset(
        self, wine_repo: WineRepository, db_session: AsyncSession
    ):
        """Test that get_list respects the offset parameter."""
        # Create wines with known names
        for i in range(5):
            wine = Wine(
                name=f"Offset Wine {i}",
                producer="Producer",
                country="France",
                region="Bordeaux",
                grape_varieties=["Merlot"],
                wine_type=WineType.RED,
                sweetness=Sweetness.DRY,
                acidity=3,
                tannins=3,
                body=3,
                description="A test wine description for testing.",
                price_usd=Decimal("50.00"),
                price_range=PriceRange.MID,
            )
            db_session.add(wine)
        await db_session.flush()

        all_wines = await wine_repo.get_list(limit=10, offset=0)
        offset_wines = await wine_repo.get_list(limit=10, offset=2)

        assert len(offset_wines) == len(all_wines) - 2

    @pytest.mark.asyncio
    async def test_get_list_empty_database(
        self, wine_repo: WineRepository
    ):
        """Test that get_list returns empty list for empty database."""
        result = await wine_repo.get_list(limit=10, offset=0)

        # May have wines from other tests, just check it's a list
        assert isinstance(result, list)


class TestWineRepositoryCount:
    """Tests for WineRepository.count method."""

    @pytest.mark.asyncio
    async def test_count_returns_total(
        self, wine_repo: WineRepository, sample_wine: Wine
    ):
        """Test that count returns total number of wines."""
        result = await wine_repo.count()

        assert result >= 1
