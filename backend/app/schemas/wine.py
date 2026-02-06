"""Pydantic schemas for wine catalog."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.wine import PriceRange, Sweetness, WineType


class WineBase(BaseModel):
    """Base wine schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    producer: str = Field(..., min_length=1, max_length=255)
    vintage_year: Optional[int] = Field(None, ge=1900, le=2030)
    country: str = Field(..., min_length=1, max_length=100)
    region: str = Field(..., min_length=1, max_length=255)
    appellation: Optional[str] = Field(None, max_length=255)
    grape_varieties: list[str] = Field(..., min_length=1)
    wine_type: WineType
    sweetness: Sweetness
    acidity: int = Field(..., ge=1, le=5)
    tannins: int = Field(..., ge=1, le=5)
    body: int = Field(..., ge=1, le=5)
    description: str = Field(..., min_length=10, max_length=2000)
    tasting_notes: Optional[str] = None
    food_pairings: Optional[list[str]] = None
    price_rub: Decimal = Field(..., gt=0)
    price_range: PriceRange
    image_url: Optional[str] = Field(None, max_length=500)


class WineCreate(WineBase):
    """Schema for creating a wine."""

    pass


class WineUpdate(BaseModel):
    """Schema for updating a wine (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    producer: Optional[str] = Field(None, min_length=1, max_length=255)
    vintage_year: Optional[int] = Field(None, ge=1900, le=2030)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    region: Optional[str] = Field(None, min_length=1, max_length=255)
    appellation: Optional[str] = Field(None, max_length=255)
    grape_varieties: Optional[list[str]] = Field(None, min_length=1)
    wine_type: Optional[WineType] = None
    sweetness: Optional[Sweetness] = None
    acidity: Optional[int] = Field(None, ge=1, le=5)
    tannins: Optional[int] = Field(None, ge=1, le=5)
    body: Optional[int] = Field(None, ge=1, le=5)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    tasting_notes: Optional[str] = None
    food_pairings: Optional[list[str]] = None
    price_rub: Optional[Decimal] = Field(None, gt=0)
    price_range: Optional[PriceRange] = None
    image_url: Optional[str] = Field(None, max_length=500)


class Wine(WineBase):
    """Full wine schema with all fields."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class WineSummary(BaseModel):
    """Summary wine schema for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    producer: str
    vintage_year: Optional[int] = None
    wine_type: WineType
    sweetness: Sweetness
    price_rub: Decimal
    country: str
    image_url: Optional[str] = None


class WineListResponse(BaseModel):
    """Response schema for wine list endpoint."""

    items: list[WineSummary]
    total: int
    limit: int
    offset: int


class WineFilters(BaseModel):
    """Filters for wine search."""

    wine_type: Optional[WineType] = None
    sweetness: Optional[Sweetness] = None
    price_min: Optional[Decimal] = Field(None, ge=0)
    price_max: Optional[Decimal] = Field(None, ge=0)
    country: Optional[str] = None
    body_min: Optional[int] = Field(None, ge=1, le=5)
    body_max: Optional[int] = Field(None, ge=1, le=5)


class SearchRequest(BaseModel):
    """Request schema for semantic search."""

    query: str = Field(..., min_length=3, max_length=500)
    limit: int = Field(5, ge=1, le=20)
    filters: Optional[WineFilters] = None


class SearchResult(BaseModel):
    """Single search result with relevance score."""

    model_config = ConfigDict(from_attributes=True)

    wine: WineSummary
    score: float = Field(..., ge=0, le=1)


class SearchResponse(BaseModel):
    """Response schema for semantic search."""

    results: list[SearchResult]
    query: str
