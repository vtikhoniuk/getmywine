"""Wine service for business logic."""
import logging
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wine import PriceRange, Sweetness, Wine, WineType
from app.repositories.wine import WineRepository
from app.schemas.wine import WineFilters
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class WineService:
    """Service for wine business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = WineRepository(db)

    async def get_wine(self, wine_id: uuid.UUID) -> Optional[Wine]:
        """Get wine by ID."""
        return await self.repo.get_by_id(wine_id)

    async def list_wines(
        self,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[WineFilters] = None,
    ) -> tuple[list[Wine], int]:
        """
        Get list of wines with optional filters.

        Returns:
            Tuple of (wines list, total count)
        """
        # Extract filter values
        wine_type = filters.wine_type if filters else None
        sweetness = filters.sweetness if filters else None
        price_min = filters.price_min if filters else None
        price_max = filters.price_max if filters else None
        country = filters.country if filters else None
        body_min = filters.body_min if filters else None
        body_max = filters.body_max if filters else None

        # Get wines and count
        wines = await self.repo.get_list(
            limit=limit,
            offset=offset,
            wine_type=wine_type,
            sweetness=sweetness,
            price_min=price_min,
            price_max=price_max,
            country=country,
            body_min=body_min,
            body_max=body_max,
        )

        total = await self.repo.count(
            wine_type=wine_type,
            sweetness=sweetness,
            price_min=price_min,
            price_max=price_max,
            country=country,
            body_min=body_min,
            body_max=body_max,
        )

        return wines, total

    async def search(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[WineFilters] = None,
    ) -> list[tuple[Wine, float]]:
        """
        Search wines using semantic similarity.

        Args:
            query: Search query text
            limit: Maximum number of results
            filters: Optional filters to apply

        Returns:
            List of (Wine, similarity_score) tuples
        """
        # Generate embedding for query
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.generate_embedding(query)

        if query_embedding is None:
            # Fallback: return filtered wines without semantic ranking
            logger.warning("Embedding generation failed, returning unranked results")
            wines = await self.repo.get_list(
                limit=limit,
                offset=0,
                wine_type=filters.wine_type if filters else None,
                sweetness=filters.sweetness if filters else None,
                price_min=filters.price_min if filters else None,
                price_max=filters.price_max if filters else None,
            )
            # Return with neutral score
            return [(wine, 0.5) for wine in wines]

        # Perform semantic search
        results = await self.repo.semantic_search(
            embedding=query_embedding,
            limit=limit,
            wine_type=filters.wine_type if filters else None,
            sweetness=filters.sweetness if filters else None,
            price_min=filters.price_min if filters else None,
            price_max=filters.price_max if filters else None,
        )

        return results
