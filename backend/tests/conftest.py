import os

# Test environment settings - MUST be before importing app
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["COOKIE_SECURE"] = "false"

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Clear settings cache to pick up test environment
from app.config import get_settings
get_settings.cache_clear()

from app.main import app  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402


# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Get tables to create (exclude Wine table for SQLite - it uses ARRAY/Vector)
    from app.models.wine import Wine
    tables_to_create = [
        table for table in Base.metadata.tables.values()
        if table.name != Wine.__tablename__
    ]

    async with engine.begin() as conn:
        for table in tables_to_create:
            await conn.run_sync(table.create, checkfirst=True)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        for table in reversed(tables_to_create):
            await conn.run_sync(table.drop, checkfirst=True)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with overridden database dependency."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def settings():
    """Get test settings."""
    return get_settings()


# Aliases for compatibility with test files
@pytest_asyncio.fixture(scope="function")
async def db_session(test_db: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Alias for test_db fixture."""
    yield test_db


@pytest_asyncio.fixture(scope="function")
async def async_client(client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """Alias for client fixture."""
    yield client


@pytest_asyncio.fixture(scope="function")
async def seed_wines(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    """Load seed wines from JSON file into test database."""
    import json
    import uuid
    from pathlib import Path

    from app.models.wine import Wine, WineType, Sweetness, PriceRange

    # Load seed data
    seed_file = Path(__file__).parent.parent / "app" / "data" / "wines_seed.json"
    with open(seed_file) as f:
        data = json.load(f)

    # Insert wines
    for wine_data in data["wines"]:
        wine = Wine(
            id=uuid.uuid4(),
            name=wine_data["name"],
            producer=wine_data["producer"],
            vintage_year=wine_data.get("vintage_year"),
            country=wine_data["country"],
            region=wine_data["region"],
            appellation=wine_data.get("appellation"),
            grape_varieties=wine_data["grape_varieties"],
            wine_type=WineType(wine_data["wine_type"]),
            sweetness=Sweetness(wine_data["sweetness"]),
            acidity=wine_data["acidity"],
            tannins=wine_data["tannins"],
            body=wine_data["body"],
            description=wine_data["description"],
            tasting_notes=wine_data.get("tasting_notes"),
            food_pairings=wine_data.get("food_pairings"),
            price_usd=wine_data["price_usd"],
            price_range=PriceRange(wine_data["price_range"]),
            image_url=wine_data.get("image_url"),
            # embedding is None for SQLite tests (no pgvector support)
            embedding=[0.0] * 1536 if hasattr(Wine, 'embedding') else None,
        )
        db_session.add(wine)

    await db_session.commit()
    yield None
