"""Unit tests for WineRepository new filters: grape_variety, food_pairing, region.

TDD Red phase — these tests should FAIL until the new parameters are added
to WineRepository.get_list().

Filter implementations:
- grape_variety -> array_to_string(grape_varieties, ',').ilike('%value%')
- food_pairing  -> array_to_string(food_pairings, ',').ilike('%value%')
- region        -> Wine.region.ilike(f'%{value}%')
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.wine import Sweetness, Wine, WineType
from app.repositories.wine import WineRepository


def _make_mock_session(return_wines: list | None = None) -> AsyncMock:
    """Create a mock AsyncSession whose execute().scalars().all() returns *return_wines*."""
    if return_wines is None:
        return_wines = []

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = return_wines
    mock_session.execute.return_value = mock_result
    return mock_session


# ---------------------------------------------------------------------------
# 1. grape_variety filter
# ---------------------------------------------------------------------------
class TestGetListGrapeVarietyFilter:
    """Tests for the grape_variety parameter on WineRepository.get_list()."""

    @pytest.mark.asyncio
    async def test_get_list_accepts_grape_variety_param(self):
        """get_list should accept grape_variety keyword argument."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        wines = await repo.get_list(grape_variety="Мальбек")

        assert wines == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_list_grape_variety_passes_value(self):
        """get_list with grape_variety should build a query (session.execute called)."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(grape_variety="Cabernet Sauvignon")

        # The repository must have called execute exactly once
        assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_get_list_grape_variety_none_is_noop(self):
        """grape_variety=None should not alter the query (default behaviour)."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(grape_variety=None)

        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 2. food_pairing filter
# ---------------------------------------------------------------------------
class TestGetListFoodPairingFilter:
    """Tests for the food_pairing parameter on WineRepository.get_list()."""

    @pytest.mark.asyncio
    async def test_get_list_accepts_food_pairing_param(self):
        """get_list should accept food_pairing keyword argument."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        wines = await repo.get_list(food_pairing="steak")

        assert wines == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_list_food_pairing_passes_value(self):
        """get_list with food_pairing should build a query (session.execute called)."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(food_pairing="pasta")

        assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_get_list_food_pairing_none_is_noop(self):
        """food_pairing=None should not alter the query (default behaviour)."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(food_pairing=None)

        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 3. region filter
# ---------------------------------------------------------------------------
class TestGetListRegionFilter:
    """Tests for the region parameter on WineRepository.get_list()."""

    @pytest.mark.asyncio
    async def test_get_list_accepts_region_param(self):
        """get_list should accept region keyword argument."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        wines = await repo.get_list(region="Bordeaux")

        assert wines == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_list_region_passes_value(self):
        """get_list with region should build a query (session.execute called)."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(region="Тоскана")

        assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_get_list_region_none_is_noop(self):
        """region=None should not alter the query (default behaviour)."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(region=None)

        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 4. Combination of new + existing filters
# ---------------------------------------------------------------------------
class TestGetListCombinedFilters:
    """Tests for combining new filters with existing ones."""

    @pytest.mark.asyncio
    async def test_grape_variety_with_wine_type_and_price_max(self):
        """get_list should accept grape_variety together with wine_type and price_max."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        wines = await repo.get_list(
            grape_variety="Пино Нуар",
            wine_type=WineType.RED,
            price_max=Decimal("3000.00"),
        )

        assert wines == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_food_pairing_with_sweetness_and_country(self):
        """get_list should accept food_pairing together with sweetness and country."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        wines = await repo.get_list(
            food_pairing="сыр",
            sweetness=Sweetness.DRY,
            country="Italy",
        )

        assert wines == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_region_with_body_range(self):
        """get_list should accept region together with body_min and body_max."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        wines = await repo.get_list(
            region="Mendoza",
            body_min=3,
            body_max=5,
        )

        assert wines == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_three_new_filters_together(self):
        """get_list should accept all three new filters at once."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        wines = await repo.get_list(
            grape_variety="Шардоне",
            food_pairing="рыба",
            region="Бургундия",
        )

        assert wines == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_filters_combined(self):
        """get_list should accept every filter parameter simultaneously."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        wines = await repo.get_list(
            limit=10,
            offset=0,
            wine_type=WineType.WHITE,
            sweetness=Sweetness.DRY,
            price_min=Decimal("500.00"),
            price_max=Decimal("5000.00"),
            country="France",
            body_min=2,
            body_max=4,
            with_image=True,
            grape_variety="Шардоне",
            food_pairing="рыба",
            region="Бургундия",
        )

        assert wines == []
        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 5. No results with impossible filter combination
# ---------------------------------------------------------------------------
class TestGetListNoResults:
    """Tests verifying empty results for impossible filter combos."""

    @pytest.mark.asyncio
    async def test_no_results_impossible_grape_and_type(self):
        """Impossible combo: Каберне Совиньон (red grape) + WHITE type returns empty."""
        mock_session = _make_mock_session(return_wines=[])
        repo = WineRepository(mock_session)

        wines = await repo.get_list(
            grape_variety="Каберне Совиньон",
            wine_type=WineType.WHITE,
            price_min=Decimal("999999.00"),
        )

        assert wines == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_results_impossible_region_and_country(self):
        """Impossible combo: region 'Bordeaux' + country 'Australia' returns empty."""
        mock_session = _make_mock_session(return_wines=[])
        repo = WineRepository(mock_session)

        wines = await repo.get_list(
            region="Bordeaux",
            country="Australia",
            food_pairing="несуществующее блюдо",
        )

        assert wines == []
        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# 6. Case-insensitive partial matching for grape_variety and food_pairing
# ---------------------------------------------------------------------------
class TestGetListCaseInsensitiveFilters:
    """Tests verifying that grape_variety and food_pairing use ilike + array_to_string.

    The LLM sends capitalized values (e.g. 'Пино Нуар') while the DB stores
    lowercase with possible suffixes ('пино нуар 51%'). The filters must handle
    both case mismatch and partial matching.
    """

    @staticmethod
    def _compile_query(mock_session: AsyncMock) -> str:
        """Extract and compile the SQLAlchemy query from mock execute call."""
        from sqlalchemy.dialects import postgresql

        query = mock_session.execute.call_args[0][0]
        return str(query.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        ))

    @pytest.mark.asyncio
    async def test_grape_variety_uses_ilike(self):
        """grape_variety filter should use ILIKE for case-insensitive matching."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(grape_variety="Пино Нуар")

        compiled = self._compile_query(mock_session)
        assert "ILIKE" in compiled

    @pytest.mark.asyncio
    async def test_grape_variety_uses_array_to_string(self):
        """grape_variety should flatten the array with array_to_string before matching."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(grape_variety="Мальбек")

        compiled = self._compile_query(mock_session)
        assert "array_to_string" in compiled

    @pytest.mark.asyncio
    async def test_grape_variety_wraps_value_with_wildcards(self):
        """The search term should be wrapped with % wildcards for partial matching."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(grape_variety="Каберне")

        compiled = self._compile_query(mock_session)
        assert "%Каберне%" in compiled

    @pytest.mark.asyncio
    async def test_food_pairing_uses_ilike(self):
        """food_pairing filter should use ILIKE for case-insensitive matching."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(food_pairing="Стейк")

        compiled = self._compile_query(mock_session)
        assert "ILIKE" in compiled

    @pytest.mark.asyncio
    async def test_food_pairing_uses_array_to_string(self):
        """food_pairing should flatten the array with array_to_string before matching."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(food_pairing="рыба")

        compiled = self._compile_query(mock_session)
        assert "array_to_string" in compiled

    @pytest.mark.asyncio
    async def test_food_pairing_wraps_value_with_wildcards(self):
        """The search term should be wrapped with % wildcards for partial matching."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(food_pairing="сыр")

        compiled = self._compile_query(mock_session)
        assert "%сыр%" in compiled

    @pytest.mark.asyncio
    async def test_grape_variety_no_contains_operator(self):
        """grape_variety should NOT use @> (contains) — it is case-sensitive."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(grape_variety="Пино Нуар")

        compiled = self._compile_query(mock_session)
        assert "@>" not in compiled

    @pytest.mark.asyncio
    async def test_food_pairing_no_overlap_operator(self):
        """food_pairing should NOT use && (overlap) — it is case-sensitive."""
        mock_session = _make_mock_session()
        repo = WineRepository(mock_session)

        await repo.get_list(food_pairing="Стейк")

        compiled = self._compile_query(mock_session)
        assert "&&" not in compiled


# ---------------------------------------------------------------------------
# T009: Tests for execute_search_wines() and format_tool_response()
# TDD Red — functions don't exist yet, tests should FAIL with AttributeError/ImportError
# ---------------------------------------------------------------------------
import json
import logging
import uuid as _uuid

from unittest.mock import AsyncMock, MagicMock, patch

from app.models.wine import Sweetness, Wine, WineType
from app.repositories.wine import WineRepository
from app.services.sommelier import SommelierService


def _make_mock_wine(**overrides) -> MagicMock:
    """Create a mock Wine object with all fields used by format_tool_response."""
    wine = MagicMock(spec=Wine)
    wine.name = overrides.get("name", "Test Wine 2020")
    wine.producer = overrides.get("producer", "Test Producer")
    wine.region = overrides.get("region", "Bordeaux")
    wine.country = overrides.get("country", "France")
    wine.vintage_year = overrides.get("vintage_year", 2020)
    wine.grape_varieties = overrides.get("grape_varieties", ["Merlot"])
    wine.wine_type = overrides.get("wine_type", WineType.RED)
    wine.sweetness = overrides.get("sweetness", Sweetness.DRY)
    wine.body = overrides.get("body", 4)
    wine.tannins = overrides.get("tannins", 3)
    wine.acidity = overrides.get("acidity", 3)
    wine.price_rub = overrides.get("price_rub", Decimal("2500.00"))
    wine.description = overrides.get("description", "A fine test wine")
    wine.tasting_notes = overrides.get("tasting_notes", "Cherry, oak")
    wine.food_pairings = overrides.get("food_pairings", ["steak", "cheese"])
    return wine


def _make_sommelier_service_with_mock_repo(return_wines: list | None = None):
    """Create a partially-mocked SommelierService for execute_search_wines tests.

    The service is a MagicMock with spec=SommelierService but with
    execute_search_wines bound to the real implementation (once it exists).
    wine_repo.get_list is an AsyncMock returning *return_wines*.
    """
    if return_wines is None:
        return_wines = []

    service = MagicMock(spec=SommelierService)
    service.wine_repo = AsyncMock(spec=WineRepository)
    service.wine_repo.get_list = AsyncMock(return_value=return_wines)

    # Bind the real method to the mock instance
    service.execute_search_wines = SommelierService.execute_search_wines.__get__(
        service, SommelierService
    )
    return service


class TestExecuteSearchWines:
    """Tests for SommelierService.execute_search_wines()."""

    @pytest.mark.asyncio
    async def test_execute_search_wines_calls_repository(self):
        """execute_search_wines should call wine_repo.get_list with mapped params."""
        mock_wines = [_make_mock_wine()]
        service = _make_sommelier_service_with_mock_repo(return_wines=mock_wines)

        arguments = {
            "wine_type": "red",
            "sweetness": "dry",
            "country": "France",
            "region": "Bordeaux",
            "grape_variety": "Merlot",
            "food_pairing": "steak",
            "price_min": 1000,
            "price_max": 5000,
        }

        result = await service.execute_search_wines(arguments)

        # Verify repository was called
        service.wine_repo.get_list.assert_called_once()

        # Inspect the keyword arguments passed to get_list
        call_kwargs = service.wine_repo.get_list.call_args.kwargs
        assert call_kwargs["wine_type"] == WineType.RED
        assert call_kwargs["sweetness"] == Sweetness.DRY
        assert call_kwargs["country"] == "France"
        assert call_kwargs["region"] == "Bordeaux"
        assert call_kwargs["grape_variety"] == "Merlot"
        assert call_kwargs["food_pairing"] == "steak"
        assert call_kwargs["price_min"] == 1000
        assert call_kwargs["price_max"] == 5000

    @pytest.mark.asyncio
    async def test_execute_search_wines_invalid_enum_ignored(self):
        """Invalid wine_type 'blue' should be silently ignored (not passed to repo)."""
        service = _make_sommelier_service_with_mock_repo(return_wines=[])

        arguments = {
            "wine_type": "blue",
            "sweetness": "dry",
        }

        result = await service.execute_search_wines(arguments)

        # Check the FIRST call (before auto-broadening may retry without sweetness)
        first_call_kwargs = service.wine_repo.get_list.call_args_list[0].kwargs
        # wine_type should NOT be in kwargs because "blue" is invalid
        assert "wine_type" not in first_call_kwargs or first_call_kwargs.get("wine_type") is None
        # sweetness IS valid and should be passed
        assert first_call_kwargs["sweetness"] == Sweetness.DRY

    @pytest.mark.asyncio
    async def test_execute_search_wines_price_min_gt_max_ignored(self):
        """When price_min > price_max, price_min should be ignored."""
        service = _make_sommelier_service_with_mock_repo(return_wines=[])

        arguments = {
            "price_min": 3000,
            "price_max": 1000,
        }

        result = await service.execute_search_wines(arguments)

        call_kwargs = service.wine_repo.get_list.call_args.kwargs
        # price_min should be dropped because 3000 > 1000
        assert "price_min" not in call_kwargs or call_kwargs.get("price_min") is None
        # price_max should still be passed
        assert call_kwargs["price_max"] == 1000

    @pytest.mark.asyncio
    async def test_execute_search_wines_logging(self):
        """execute_search_wines should log the tool name and result count."""
        mock_wines = [_make_mock_wine(), _make_mock_wine(name="Second Wine")]
        service = _make_sommelier_service_with_mock_repo(return_wines=mock_wines)

        arguments = {"wine_type": "red"}

        with patch("app.services.sommelier.logger") as mock_logger:
            result = await service.execute_search_wines(arguments)

            # logger.info should be called at least once with tool name and count
            mock_logger.info.assert_called()
            log_call_args = [
                str(call) for call in mock_logger.info.call_args_list
            ]
            log_text = " ".join(log_call_args)
            assert "search_wines" in log_text.lower() or "2" in log_text


class TestFormatToolResponse:
    """Tests for SommelierService.format_tool_response() (or standalone function)."""

    def _get_format_tool_response(self):
        """Import format_tool_response — will fail until implemented."""
        from app.services.sommelier import format_tool_response
        return format_tool_response

    def test_format_tool_response_structure(self):
        """format_tool_response should return JSON with 'found', 'wines', 'filters_applied'."""
        format_tool_response = self._get_format_tool_response()

        wines = [_make_mock_wine(), _make_mock_wine(name="Wine Two")]
        filters_applied = {"wine_type": "red", "country": "France"}

        result = format_tool_response(wines, filters_applied)
        parsed = json.loads(result)

        assert "found" in parsed
        assert "wines" in parsed
        assert "filters_applied" in parsed
        assert parsed["found"] == 2
        assert len(parsed["wines"]) == 2
        assert parsed["filters_applied"] == filters_applied

    def test_format_tool_response_empty(self):
        """format_tool_response with empty wines list should return found=0."""
        format_tool_response = self._get_format_tool_response()

        result = format_tool_response([], {})
        parsed = json.loads(result)

        assert parsed["found"] == 0
        assert parsed["wines"] == []


# ---------------------------------------------------------------------------
# T017: Tests for execute_semantic_search()
# TDD Red — function doesn't exist yet, tests should FAIL with AttributeError
# ---------------------------------------------------------------------------


def _make_sommelier_service_for_semantic_search(
    search_results: list | None = None,
    embedding: list[float] | None = None,
):
    """Create a SommelierService with mocked llm_service and wine_repo for semantic search.

    search_results: list of (wine, similarity_score) tuples returned by semantic_search()
    embedding: embedding vector returned by get_query_embedding()
    """
    if search_results is None:
        search_results = []
    if embedding is None:
        embedding = [0.1] * 1024

    service = MagicMock(spec=SommelierService)
    service.wine_repo = AsyncMock(spec=WineRepository)
    service.wine_repo.semantic_search = AsyncMock(return_value=search_results)
    service.llm_service = MagicMock()
    service.llm_service.get_query_embedding = AsyncMock(return_value=embedding)

    # Bind the real method
    service.execute_semantic_search = SommelierService.execute_semantic_search.__get__(
        service, SommelierService
    )
    return service


class TestExecuteSemanticSearch:
    """Tests for SommelierService.execute_semantic_search()."""

    @pytest.mark.asyncio
    async def test_execute_semantic_search_generates_embedding(self):
        """execute_semantic_search should call get_query_embedding with the query text."""
        service = _make_sommelier_service_for_semantic_search()

        arguments = {"query": "лёгкое и освежающее вино на лето"}

        await service.execute_semantic_search(arguments)

        service.llm_service.get_query_embedding.assert_called_once_with(
            "лёгкое и освежающее вино на лето"
        )

    @pytest.mark.asyncio
    async def test_execute_semantic_search_calls_repository(self):
        """execute_semantic_search should call wine_repo.semantic_search with embedding."""
        embedding = [0.5] * 1024
        service = _make_sommelier_service_for_semantic_search(embedding=embedding)

        arguments = {"query": "элегантное красное вино"}

        await service.execute_semantic_search(arguments)

        service.wine_repo.semantic_search.assert_called_once()
        call_kwargs = service.wine_repo.semantic_search.call_args
        # First positional arg should be the embedding
        assert call_kwargs[0][0] == embedding or call_kwargs.kwargs.get("embedding") == embedding

    @pytest.mark.asyncio
    async def test_execute_semantic_search_passes_optional_filters(self):
        """Optional wine_type and price_max should be forwarded to repository."""
        service = _make_sommelier_service_for_semantic_search()

        arguments = {
            "query": "вино с нотами ванили",
            "wine_type": "red",
            "price_max": 3000,
        }

        await service.execute_semantic_search(arguments)

        call_kwargs = service.wine_repo.semantic_search.call_args.kwargs
        assert call_kwargs.get("wine_type") is not None
        assert call_kwargs.get("price_max") == 3000

    @pytest.mark.asyncio
    async def test_execute_semantic_search_response_includes_similarity(self):
        """Response should include similarity_score for each wine."""
        mock_wine = _make_mock_wine(name="Elegant Merlot 2020")
        service = _make_sommelier_service_for_semantic_search(
            search_results=[(mock_wine, 0.92)]
        )

        arguments = {"query": "элегантное вино"}

        result = await service.execute_semantic_search(arguments)
        parsed = json.loads(result)

        assert parsed["found"] == 1
        assert len(parsed["wines"]) == 1
        assert "similarity_score" in parsed["wines"][0]
        assert parsed["wines"][0]["similarity_score"] == 0.92

    @pytest.mark.asyncio
    async def test_execute_semantic_search_empty_results(self):
        """No matching wines should return found=0."""
        service = _make_sommelier_service_for_semantic_search(search_results=[])

        arguments = {"query": "несуществующий вкус"}

        result = await service.execute_semantic_search(arguments)
        parsed = json.loads(result)

        assert parsed["found"] == 0
        assert parsed["wines"] == []

    @pytest.mark.asyncio
    async def test_execute_semantic_search_logging(self):
        """execute_semantic_search should log the tool name and result count."""
        mock_wine = _make_mock_wine()
        service = _make_sommelier_service_for_semantic_search(
            search_results=[(mock_wine, 0.85)]
        )

        arguments = {"query": "фруктовое вино"}

        with patch("app.services.sommelier.logger") as mock_logger:
            await service.execute_semantic_search(arguments)

            mock_logger.info.assert_called()
            log_text = " ".join(str(c) for c in mock_logger.info.call_args_list)
            assert "semantic_search" in log_text.lower() or "1" in log_text
