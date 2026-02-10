"""Wine repository for database operations."""
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wine import PriceRange, Sweetness, Wine, WineType


class WineRepository:
    """Repository for wine database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, wine_id: uuid.UUID) -> Optional[Wine]:
        """Get wine by ID."""
        result = await self.db.execute(
            select(Wine).where(Wine.id == wine_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, wine_ids: list[uuid.UUID]) -> list[Wine]:
        """Get wines by list of IDs, preserving order."""
        if not wine_ids:
            return []
        result = await self.db.execute(
            select(Wine).where(Wine.id.in_(wine_ids))
        )
        wines_dict = {wine.id: wine for wine in result.scalars().all()}
        # Preserve original order
        return [wines_dict[wid] for wid in wine_ids if wid in wines_dict]

    async def get_list(
        self,
        limit: int = 20,
        offset: int = 0,
        wine_type: Optional[WineType] = None,
        sweetness: Optional[Sweetness] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        country: Optional[str] = None,
        body_min: Optional[int] = None,
        body_max: Optional[int] = None,
        with_image: Optional[bool] = None,
        grape_variety: Optional[str] = None,
        food_pairing: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list[Wine]:
        """Get list of wines with optional filters."""
        query = select(Wine)

        # Apply filters
        if wine_type is not None:
            query = query.where(Wine.wine_type == wine_type)
        if sweetness is not None:
            query = query.where(Wine.sweetness == sweetness)
        if price_min is not None:
            query = query.where(Wine.price_rub >= price_min)
        if price_max is not None:
            query = query.where(Wine.price_rub <= price_max)
        if country is not None:
            query = query.where(Wine.country == country)
        if body_min is not None:
            query = query.where(Wine.body >= body_min)
        if body_max is not None:
            query = query.where(Wine.body <= body_max)
        if with_image is True:
            query = query.where(Wine.image_url.isnot(None))
        if grape_variety is not None:
            # Case-insensitive partial match (handles "Пино Нуар" vs "пино нуар 51%")
            query = query.where(
                func.array_to_string(Wine.grape_varieties, ',').ilike(f"%{grape_variety}%")
            )
        if food_pairing is not None:
            # Case-insensitive partial match for food pairings
            query = query.where(
                func.array_to_string(Wine.food_pairings, ',').ilike(f"%{food_pairing}%")
            )
        if region is not None:
            query = query.where(Wine.region.ilike(f"%{region}%"))

        # Apply pagination
        query = query.order_by(Wine.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(
        self,
        wine_type: Optional[WineType] = None,
        sweetness: Optional[Sweetness] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        country: Optional[str] = None,
        body_min: Optional[int] = None,
        body_max: Optional[int] = None,
    ) -> int:
        """Count wines with optional filters."""
        query = select(func.count(Wine.id))

        # Apply same filters as get_list
        if wine_type is not None:
            query = query.where(Wine.wine_type == wine_type)
        if sweetness is not None:
            query = query.where(Wine.sweetness == sweetness)
        if price_min is not None:
            query = query.where(Wine.price_rub >= price_min)
        if price_max is not None:
            query = query.where(Wine.price_rub <= price_max)
        if country is not None:
            query = query.where(Wine.country == country)
        if body_min is not None:
            query = query.where(Wine.body >= body_min)
        if body_max is not None:
            query = query.where(Wine.body <= body_max)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def create(self, wine: Wine) -> Wine:
        """Create a new wine."""
        self.db.add(wine)
        await self.db.flush()
        await self.db.refresh(wine)
        return wine

    async def semantic_search(
        self,
        embedding: list[float],
        limit: int = 5,
        wine_type: Optional[WineType] = None,
        sweetness: Optional[Sweetness] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
    ) -> list[tuple[Wine, float]]:
        """
        Search wines by semantic similarity using pgvector.

        Args:
            embedding: Query embedding vector
            limit: Maximum number of results
            wine_type: Optional filter by wine type
            sweetness: Optional filter by sweetness
            price_min: Optional minimum price filter
            price_max: Optional maximum price filter

        Returns:
            List of (Wine, similarity_score) tuples, ordered by similarity
        """
        # Build query with cosine distance
        # pgvector uses <=> for cosine distance (lower = more similar)
        # Convert to similarity: 1 - distance
        distance = Wine.embedding.cosine_distance(embedding)
        query = select(Wine, (1 - distance).label("similarity")).where(
            Wine.embedding.isnot(None)
        )

        # Apply filters
        if wine_type is not None:
            query = query.where(Wine.wine_type == wine_type)
        if sweetness is not None:
            query = query.where(Wine.sweetness == sweetness)
        if price_min is not None:
            query = query.where(Wine.price_rub >= price_min)
        if price_max is not None:
            query = query.where(Wine.price_rub <= price_max)

        # Order by similarity (higher is better) and limit
        query = query.order_by(distance).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        return [(row[0], float(row[1])) for row in rows]

    async def update_embedding(
        self, wine_id: uuid.UUID, embedding: list[float]
    ) -> Optional[Wine]:
        """Update wine's embedding vector."""
        wine = await self.get_by_id(wine_id)
        if wine:
            wine.embedding = embedding
            await self.db.flush()
            await self.db.refresh(wine)
        return wine
