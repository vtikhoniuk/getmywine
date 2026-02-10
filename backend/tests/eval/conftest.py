"""Fixtures for eval tests (real LLM + real PostgreSQL)."""

import socket
from typing import AsyncGenerator
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


def _has_real_backend() -> tuple[bool, str]:
    """Check if real LLM + PostgreSQL are available and reachable."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        return False, "OPENROUTER_API_KEY not set"
    if "sqlite" in settings.database_url:
        return False, "Real PostgreSQL required (DATABASE_URL points to SQLite)"

    # Verify the DB host is actually reachable (e.g. not a Docker-only hostname)
    parsed = urlparse(settings.database_url.replace("+asyncpg", ""))
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    try:
        socket.getaddrinfo(host, port)
    except socket.gaierror:
        return False, f"PostgreSQL host '{host}:{port}' is not reachable"

    return True, ""


_AVAILABLE, _SKIP_REASON = _has_real_backend()


def pytest_collection_modifyitems(config, items):
    """Skip all eval tests when real backend is not available."""
    if _AVAILABLE:
        return
    skip_marker = pytest.mark.skip(reason=_SKIP_REASON)
    for item in items:
        if "/eval/" in str(item.fspath):
            item.add_marker(skip_marker)


@pytest_asyncio.fixture
async def eval_db() -> AsyncGenerator[AsyncSession, None]:
    """Real PostgreSQL session (uses DATABASE_URL from .env)."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def sommelier_service(eval_db: AsyncSession):
    """SommelierService wired to real PostgreSQL + real LLM."""
    from app.services.llm import reset_llm_service
    from app.services.sommelier import SommelierService

    # Reset singletons so they pick up real credentials
    reset_llm_service()
    SommelierService._wines_available = None

    service = SommelierService(eval_db)
    yield service

    SommelierService._wines_available = None
    reset_llm_service()


@pytest_asyncio.fixture
async def catalog_wines(eval_db: AsyncSession) -> list:
    """Load all wine names from the real catalog."""
    from sqlalchemy import select
    from app.models.wine import Wine

    result = await eval_db.execute(select(Wine))
    return list(result.scalars().all())


class ToolCallSpy:
    """Spy that wraps SommelierService tool execution methods.

    Records every tool call (name + arguments) while still executing
    the real logic underneath.
    """

    def __init__(self, service):
        self.calls: list[tuple[str, dict]] = []
        self._service = service
        self._orig_search = service.execute_search_wines
        self._orig_semantic = service.execute_semantic_search

        # Monkey-patch
        service.execute_search_wines = self._spy_search
        service.execute_semantic_search = self._spy_semantic

    async def _spy_search(self, arguments: dict) -> str:
        self.calls.append(("search_wines", dict(arguments)))
        return await self._orig_search(arguments)

    async def _spy_semantic(self, arguments: dict) -> str:
        self.calls.append(("semantic_search", dict(arguments)))
        return await self._orig_semantic(arguments)

    @property
    def tool_names(self) -> list[str]:
        return [name for name, _ in self.calls]

    @property
    def first_tool(self) -> str | None:
        return self.calls[0][0] if self.calls else None

    @property
    def first_args(self) -> dict | None:
        return self.calls[0][1] if self.calls else None

    def search_calls(self) -> list[dict]:
        return [args for name, args in self.calls if name == "search_wines"]

    def semantic_calls(self) -> list[dict]:
        return [args for name, args in self.calls if name == "semantic_search"]


@pytest.fixture
def tool_spy(sommelier_service) -> ToolCallSpy:
    """Attach spy to sommelier service tool execution methods."""
    return ToolCallSpy(sommelier_service)
