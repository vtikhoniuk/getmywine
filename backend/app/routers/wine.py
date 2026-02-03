"""Wine router for API endpoints."""
import uuid
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.wine import Sweetness, WineType
from app.schemas.wine import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    Wine as WineSchema,
    WineFilters,
    WineListResponse,
    WineSummary,
)
from app.services.wine import WineService

router = APIRouter(prefix="/api/v1/wines", tags=["wines"])


@router.get("", response_model=WineListResponse)
async def list_wines(
    db: Annotated[AsyncSession, Depends(get_db)],
    wine_type: Optional[WineType] = Query(None, description="Filter by wine type"),
    sweetness: Optional[Sweetness] = Query(None, description="Filter by sweetness"),
    price_min: Optional[Decimal] = Query(None, ge=0, description="Minimum price USD"),
    price_max: Optional[Decimal] = Query(None, ge=0, description="Maximum price USD"),
    country: Optional[str] = Query(None, description="Filter by country"),
    body_min: Optional[int] = Query(None, ge=1, le=5, description="Minimum body (1-5)"),
    body_max: Optional[int] = Query(None, ge=1, le=5, description="Maximum body (1-5)"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    """
    List wines with optional filters and pagination.

    Returns a paginated list of wines matching the specified criteria.
    """
    service = WineService(db)

    filters = WineFilters(
        wine_type=wine_type,
        sweetness=sweetness,
        price_min=price_min,
        price_max=price_max,
        country=country,
        body_min=body_min,
        body_max=body_max,
    )

    wines, total = await service.list_wines(
        limit=limit,
        offset=offset,
        filters=filters,
    )

    return WineListResponse(
        items=[WineSummary.model_validate(wine) for wine in wines],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/search", response_model=SearchResponse)
async def search_wines(
    request: SearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Semantic search for wines.

    Uses AI embeddings to find wines matching the search query.
    Optionally filter results by wine type and price.
    """
    service = WineService(db)

    results = await service.search(
        query=request.query,
        limit=request.limit,
        filters=request.filters,
    )

    return SearchResponse(
        results=[
            SearchResult(
                wine=WineSummary.model_validate(wine),
                score=score,
            )
            for wine, score in results
        ],
        query=request.query,
    )


@router.get("/{wine_id}", response_model=WineSchema)
async def get_wine(
    wine_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get wine by ID.

    Returns full details for a specific wine.
    """
    service = WineService(db)
    wine = await service.get_wine(wine_id)

    if wine is None:
        raise HTTPException(status_code=404, detail="Wine not found")

    return WineSchema.model_validate(wine)
