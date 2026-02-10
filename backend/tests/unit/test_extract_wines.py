"""Tests for simplified _extract_wines_from_response().

After name normalization, matching should use direct wine.name search
in the LLM response text (single-level matching). The old 3-level
workaround (strip "Вино" prefix, strip vintage year) should be removed.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.wine import Wine


def _make_wine(name: str, wine_id: str | None = None) -> MagicMock:
    """Create a mock Wine object with the given name."""
    wine = MagicMock(spec=Wine)
    wine.id = uuid.UUID(wine_id) if wine_id else uuid.uuid4()
    wine.name = name
    return wine


class TestExtractWinesFromResponse:
    """Tests for the simplified wine extraction logic."""

    @pytest.fixture
    def service(self):
        """Create a TelegramBotService instance with mocked dependencies."""
        from app.services.telegram_bot import TelegramBotService

        mock_db = AsyncMock()
        svc = TelegramBotService(db=mock_db)
        return svc

    @pytest.mark.asyncio
    async def test_direct_name_match(self, service):
        """Wine name found in LLM text should be matched."""
        wines = [
            _make_wine("Malbec"),
            _make_wine("Chianti Castiglioni"),
            _make_wine("El Picaro"),
        ]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_list = AsyncMock(return_value=wines)

        response_text = "Рекомендую Malbec — отличное аргентинское вино."
        result = await service._extract_wines_from_response(response_text)

        assert len(result) == 1
        assert result[0].name == "Malbec"

    @pytest.mark.asyncio
    async def test_no_match_when_name_absent(self, service):
        """No match when wine name is not in response text."""
        wines = [_make_wine("Malbec"), _make_wine("El Picaro")]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_list = AsyncMock(return_value=wines)

        response_text = "Попробуйте Рислинг от немецкого производителя."
        result = await service._extract_wines_from_response(response_text)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_ordering_by_position_in_text(self, service):
        """Wines should be ordered by their position in the response text."""
        wines = [
            _make_wine("Chianti Castiglioni"),
            _make_wine("Malbec"),
            _make_wine("El Picaro"),
        ]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_list = AsyncMock(return_value=wines)

        response_text = (
            "Первым советую El Picaro, затем Malbec, "
            "и наконец Chianti Castiglioni."
        )
        result = await service._extract_wines_from_response(response_text)

        assert len(result) == 3
        assert result[0].name == "El Picaro"
        assert result[1].name == "Malbec"
        assert result[2].name == "Chianti Castiglioni"

    @pytest.mark.asyncio
    async def test_max_wines_limit(self, service):
        """Should return at most max_wines results."""
        wines = [
            _make_wine("Malbec"),
            _make_wine("El Picaro"),
            _make_wine("Chianti Castiglioni"),
            _make_wine("Герцъ"),
            _make_wine("Le Rime"),
        ]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_list = AsyncMock(return_value=wines)

        response_text = (
            "Рекомендую: Malbec, El Picaro, Chianti Castiglioni, "
            "Герцъ и Le Rime."
        )
        result = await service._extract_wines_from_response(
            response_text, max_wines=3
        )

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_multiple_wines_matched(self, service):
        """Multiple wines should be matched when present in text."""
        wines = [
            _make_wine("Malbec"),
            _make_wine("Петрикор Красное"),
            _make_wine("Chianti Castiglioni"),
        ]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_list = AsyncMock(return_value=wines)

        response_text = (
            "Вот три вина:\n"
            "1. Malbec — аргентинский красный\n"
            "2. Петрикор Красное — российское красное\n"
            "3. Chianti Castiglioni — итальянская классика"
        )
        result = await service._extract_wines_from_response(response_text)

        assert len(result) == 3
        names = [w.name for w in result]
        assert "Malbec" in names
        assert "Петрикор Красное" in names
        assert "Chianti Castiglioni" in names

    @pytest.mark.asyncio
    async def test_no_duplicate_matches(self, service):
        """Same wine mentioned twice should only appear once."""
        wines = [_make_wine("Malbec")]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_list = AsyncMock(return_value=wines)

        response_text = "Malbec — отличное вино. Malbec подходит к стейку."
        result = await service._extract_wines_from_response(response_text)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_normalized_names_match_directly(self, service):
        """Normalized names (without prefix) should match directly."""
        wines = [
            _make_wine("Балаклава Брют Резерв"),
            _make_wine("Bruni Prosecco Brut"),
        ]
        service.wine_repo = AsyncMock()
        service.wine_repo.get_list = AsyncMock(return_value=wines)

        response_text = (
            "Для праздника рекомендую Балаклава Брют Резерв "
            "или Bruni Prosecco Brut."
        )
        result = await service._extract_wines_from_response(response_text)

        assert len(result) == 2
