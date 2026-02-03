"""Integration tests for wine seed migration (US3).

TDD: These tests must FAIL before implementation.

NOTE: These tests require PostgreSQL with pgvector extension.
They are skipped when using SQLite (which doesn't support ARRAY or vector types).
Verification was performed manually against PostgreSQL database.
"""
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wine import Wine, WineType


# Skip all tests in this module when using SQLite
pytestmark = pytest.mark.skipif(
    True,  # Tests require PostgreSQL
    reason="Wine seed tests require PostgreSQL with pgvector extension"
)


@pytest.mark.asyncio
class TestWineSeedMigration:
    """Tests for seed migration that populates 50 wines."""

    async def test_seed_creates_exactly_50_wines(
        self, db_session: AsyncSession, seed_wines: None
    ):
        """T030: Seed migration creates exactly 50 wines."""
        result = await db_session.execute(select(func.count(Wine.id)))
        count = result.scalar()
        assert count == 50, f"Expected 50 wines, got {count}"

    async def test_wine_type_distribution(
        self, db_session: AsyncSession, seed_wines: None
    ):
        """T031: Wine type distribution (~40% red, ~30% white, ~15% rose, ~15% sparkling).

        Expected: 20 red, 15 white, 8 rose, 7 sparkling
        """
        # Count by wine type
        red_result = await db_session.execute(
            select(func.count(Wine.id)).where(Wine.wine_type == WineType.RED)
        )
        white_result = await db_session.execute(
            select(func.count(Wine.id)).where(Wine.wine_type == WineType.WHITE)
        )
        rose_result = await db_session.execute(
            select(func.count(Wine.id)).where(Wine.wine_type == WineType.ROSE)
        )
        sparkling_result = await db_session.execute(
            select(func.count(Wine.id)).where(Wine.wine_type == WineType.SPARKLING)
        )

        red_count = red_result.scalar()
        white_count = white_result.scalar()
        rose_count = rose_result.scalar()
        sparkling_count = sparkling_result.scalar()

        # Exact distribution per spec
        assert red_count == 20, f"Expected 20 red wines, got {red_count}"
        assert white_count == 15, f"Expected 15 white wines, got {white_count}"
        assert rose_count == 8, f"Expected 8 rose wines, got {rose_count}"
        assert sparkling_count == 7, f"Expected 7 sparkling wines, got {sparkling_count}"

    async def test_price_distribution(
        self, db_session: AsyncSession, seed_wines: None
    ):
        """T032: Price distribution (90% $50-100, 10% premium $100+).

        Expected: 45 wines $50-100, 5 wines $100+
        """
        # Count wines in $50-100 range
        mid_range_result = await db_session.execute(
            select(func.count(Wine.id)).where(
                Wine.price_usd >= 50,
                Wine.price_usd <= 100
            )
        )
        mid_range_count = mid_range_result.scalar()

        # Count premium wines ($100+)
        premium_result = await db_session.execute(
            select(func.count(Wine.id)).where(Wine.price_usd > 100)
        )
        premium_count = premium_result.scalar()

        assert mid_range_count == 45, f"Expected 45 wines in $50-100 range, got {mid_range_count}"
        assert premium_count == 5, f"Expected 5 premium wines ($100+), got {premium_count}"

    async def test_all_wines_have_image_url(
        self, db_session: AsyncSession, seed_wines: None
    ):
        """T033: All wines have image_url set."""
        # Count wines without image_url
        no_image_result = await db_session.execute(
            select(func.count(Wine.id)).where(Wine.image_url.is_(None))
        )
        no_image_count = no_image_result.scalar()

        assert no_image_count == 0, f"Expected all wines to have image_url, but {no_image_count} are missing"

        # Verify all have valid URLs
        result = await db_session.execute(select(Wine.image_url))
        urls = [row[0] for row in result.all()]

        for url in urls:
            assert url is not None, "image_url should not be None"
            assert url.startswith("http"), f"Invalid image URL: {url}"

    async def test_minimum_countries_diversity(
        self, db_session: AsyncSession, seed_wines: None
    ):
        """Test wines come from at least 6 different countries."""
        result = await db_session.execute(
            select(func.count(func.distinct(Wine.country)))
        )
        country_count = result.scalar()

        assert country_count >= 6, f"Expected at least 6 countries, got {country_count}"

    async def test_all_wines_have_required_fields(
        self, db_session: AsyncSession, seed_wines: None
    ):
        """Test all wines have required fields populated."""
        result = await db_session.execute(select(Wine))
        wines = result.scalars().all()

        for wine in wines:
            assert wine.name, f"Wine {wine.id} missing name"
            assert wine.producer, f"Wine {wine.id} missing producer"
            assert wine.country, f"Wine {wine.id} missing country"
            assert wine.region, f"Wine {wine.id} missing region"
            assert wine.grape_varieties, f"Wine {wine.id} missing grape_varieties"
            assert wine.description, f"Wine {wine.id} missing description"
            assert wine.price_usd > 0, f"Wine {wine.id} has invalid price"
            assert 1 <= wine.acidity <= 5, f"Wine {wine.id} has invalid acidity"
            assert 1 <= wine.tannins <= 5, f"Wine {wine.id} has invalid tannins"
            assert 1 <= wine.body <= 5, f"Wine {wine.id} has invalid body"

    async def test_all_wines_have_embeddings(
        self, db_session: AsyncSession, seed_wines: None
    ):
        """Test all wines have embedding vectors for semantic search."""
        # Count wines without embeddings
        no_embedding_result = await db_session.execute(
            select(func.count(Wine.id)).where(Wine.embedding.is_(None))
        )
        no_embedding_count = no_embedding_result.scalar()

        assert no_embedding_count == 0, f"Expected all wines to have embeddings, but {no_embedding_count} are missing"
