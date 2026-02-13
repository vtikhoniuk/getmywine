"""Tests for _extract_wines_from_response().

Uses structured output wine_ids for direct ID lookup.
Empty wine_ids [] means no wines (informational/off_topic response).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.wine import Wine

# Fixed UUIDs for deterministic tests
_ID1 = "11111111-1111-1111-1111-111111111111"
_ID2 = "22222222-2222-2222-2222-222222222222"
_ID3 = "33333333-3333-3333-3333-333333333333"
_ID4 = "44444444-4444-4444-4444-444444444444"


def _make_wine(name: str, wine_id: str) -> MagicMock:
    """Create a mock Wine object with the given name and ID."""
    wine = MagicMock(spec=Wine)
    wine.id = uuid.UUID(wine_id)
    wine.name = name
    return wine


class TestExtractWinesFromResponse:
    """Tests for structured wine extraction by ID."""

    @pytest.fixture
    def service(self):
        """Create a TelegramBotService instance with mocked dependencies."""
        from app.services.telegram_bot import TelegramBotService

        mock_db = AsyncMock()
        svc = TelegramBotService(db=mock_db)
        return svc

    @pytest.mark.asyncio
    async def test_single_wine_id_lookup(self, service):
        """wine_ids with valid ID → matched wine returned."""
        wines = [_make_wine("Malbec", _ID1)]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_by_ids = AsyncMock(return_value=wines)

        result = await service._extract_wines_from_response(
            "", wine_ids=[_ID1],
        )

        assert len(result) == 1
        assert result[0].name == "Malbec"
        service.wine_repo.get_by_ids.assert_called_once_with([uuid.UUID(_ID1)])

    @pytest.mark.asyncio
    async def test_multiple_wine_ids(self, service):
        """Multiple wine_ids → all matched wines returned in order."""
        wines = [
            _make_wine("Chianti Castiglioni", _ID3),
            _make_wine("Malbec", _ID1),
            _make_wine("Петрикор Красное", _ID2),
        ]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_by_ids = AsyncMock(return_value=wines)

        result = await service._extract_wines_from_response(
            "", wine_ids=[_ID3, _ID1, _ID2],
        )

        assert len(result) == 3
        # Order is preserved by get_by_ids
        assert result[0].name == "Chianti Castiglioni"
        assert result[1].name == "Malbec"
        assert result[2].name == "Петрикор Красное"

    @pytest.mark.asyncio
    async def test_max_wines_limit(self, service):
        """Should pass at most max_wines IDs to repo."""
        wines = [
            _make_wine("Malbec", _ID1),
            _make_wine("El Picaro", _ID2),
            _make_wine("Chianti Castiglioni", _ID3),
        ]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_by_ids = AsyncMock(return_value=wines)

        result = await service._extract_wines_from_response(
            "",
            wine_ids=[_ID1, _ID2, _ID3, _ID4],
            max_wines=3,
        )

        # Only first 3 IDs should be passed
        service.wine_repo.get_by_ids.assert_called_once_with(
            [uuid.UUID(_ID1), uuid.UUID(_ID2), uuid.UUID(_ID3)]
        )

    @pytest.mark.asyncio
    async def test_invalid_uuid_skipped(self, service):
        """Invalid wine_id string → skipped, valid ones still looked up."""
        wines = [_make_wine("Malbec", _ID1)]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_by_ids = AsyncMock(return_value=wines)

        result = await service._extract_wines_from_response(
            "", wine_ids=[_ID1, "not-a-uuid", ""],
        )

        assert len(result) == 1
        service.wine_repo.get_by_ids.assert_called_once_with([uuid.UUID(_ID1)])

    @pytest.mark.asyncio
    async def test_empty_wine_ids_returns_empty(self, service):
        """Empty wine_ids [] (informational/off_topic) → no wines, no DB query."""
        service.wine_repo = AsyncMock()

        result = await service._extract_wines_from_response(
            "Оранжевые вина — это белые вина, сделанные красным способом.",
            wine_ids=[],
        )

        assert result == []
        service.wine_repo.get_by_ids.assert_not_called()

    @pytest.mark.asyncio
    async def test_none_wine_ids_returns_empty(self, service):
        """wine_ids=None → no wines, no DB query."""
        service.wine_repo = AsyncMock()

        result = await service._extract_wines_from_response(
            "Любой текст", wine_ids=None,
        )

        assert result == []
        service.wine_repo.get_by_ids.assert_not_called()

    @pytest.mark.asyncio
    async def test_informational_with_wine_mention_no_card(self, service):
        """Informational response mentioning a wine name in text → no wine cards.

        This is the exact bug scenario: user asks about orange wines,
        LLM mentions "Loco Cimbali Orange" in educational text but
        returns wine_ids=[] because it's informational.
        """
        service.wine_repo = AsyncMock()

        response_text = (
            "Оранжевые вина — это особая категория вин. "
            "Хотите попробовать Loco Cimbali Orange или другие оранжевые вина?"
        )
        result = await service._extract_wines_from_response(
            response_text, wine_ids=[],
        )

        assert result == []
