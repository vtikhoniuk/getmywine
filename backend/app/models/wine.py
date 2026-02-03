"""Wine model and related enums."""
import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WineType(str, enum.Enum):
    """Wine type enum."""

    RED = "red"
    WHITE = "white"
    ROSE = "rose"
    SPARKLING = "sparkling"


class Sweetness(str, enum.Enum):
    """Wine sweetness level enum."""

    DRY = "dry"
    SEMI_DRY = "semi_dry"
    SEMI_SWEET = "semi_sweet"
    SWEET = "sweet"


class PriceRange(str, enum.Enum):
    """Wine price range enum."""

    BUDGET = "budget"  # < $30
    MID = "mid"  # $30-100
    PREMIUM = "premium"  # > $100


class Wine(Base):
    """Wine model for the catalog."""

    __tablename__ = "wines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    producer: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    vintage_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    region: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    appellation: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    grape_varieties: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)),
        nullable=False,
    )
    wine_type: Mapped[WineType] = mapped_column(
        Enum(
            WineType,
            name="wine_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    sweetness: Mapped[Sweetness] = mapped_column(
        Enum(
            Sweetness,
            name="sweetness",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    acidity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    tannins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    body: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    tasting_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    food_pairings: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
    )
    price_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        index=True,
    )
    price_range: Mapped[PriceRange] = mapped_column(
        Enum(
            PriceRange,
            name="price_range",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(1536),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "vintage_year IS NULL OR (vintage_year >= 1900 AND vintage_year <= 2030)",
            name="ck_wines_vintage_year",
        ),
        CheckConstraint("acidity >= 1 AND acidity <= 5", name="ck_wines_acidity"),
        CheckConstraint("tannins >= 1 AND tannins <= 5", name="ck_wines_tannins"),
        CheckConstraint("body >= 1 AND body <= 5", name="ck_wines_body"),
        CheckConstraint("price_usd > 0", name="ck_wines_price_usd"),
    )

    def __repr__(self) -> str:
        return f"<Wine {self.id} name={self.name}>"
