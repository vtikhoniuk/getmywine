"""Unit tests for SessionNamingService.

Tests:
- T025: generate_session_title() generates proper titles
- T026: Fallback to date when LLM fails
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.session_naming import (
    RUSSIAN_MONTHS,
    SessionNamingService,
    get_session_naming_service,
    reset_session_naming_service,
)


@pytest.fixture
def naming_service():
    """Create a fresh naming service for each test."""
    reset_session_naming_service()
    return SessionNamingService()


@pytest.mark.asyncio
class TestGenerateSessionTitle:
    """T025: Tests for generate_session_title()."""

    async def test_generates_title_from_llm(self, naming_service):
        """Should generate title using LLM."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(return_value="Вино к стейку")

        with patch.object(naming_service, "_llm", mock_llm):
            title = await naming_service.generate_session_title(
                user_message="Посоветуй вино к стейку",
                ai_response="Для стейка отлично подойдет красное вино...",
            )

        assert title == "Вино к стейку"
        mock_llm.generate.assert_called_once()

    async def test_cleans_title_quotes(self, naming_service):
        """Should remove quotes from generated title."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(return_value='"Бордо на ДР"')

        with patch.object(naming_service, "_llm", mock_llm):
            title = await naming_service.generate_session_title(
                user_message="test",
                ai_response="test",
            )

        assert title == "Бордо на ДР"

    async def test_truncates_long_title(self, naming_service):
        """Should truncate title to 30 characters."""
        long_title = "Очень длинное название для сессии которое не влезет"
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(return_value=long_title)

        with patch.object(naming_service, "_llm", mock_llm):
            title = await naming_service.generate_session_title(
                user_message="test",
                ai_response="test",
            )

        assert len(title) <= 30

    async def test_uses_date_fallback_when_llm_unavailable(self, naming_service):
        """Should use date fallback when LLM is not available."""
        mock_llm = MagicMock()
        mock_llm.is_available = False

        with patch.object(naming_service, "_llm", mock_llm):
            title = await naming_service.generate_session_title(
                user_message="test",
                ai_response="test",
            )

        # Should be in format "D месяца"
        assert any(month in title for month in RUSSIAN_MONTHS)


class TestDateFallback:
    """T026: Tests for date fallback when LLM fails."""

    @pytest.mark.asyncio
    async def test_fallback_on_llm_error(self, naming_service):
        """Should fallback to date when LLM raises error."""
        from app.services.llm import LLMError

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(side_effect=LLMError("API error"))

        with patch.object(naming_service, "_llm", mock_llm):
            title = await naming_service.generate_session_title(
                user_message="test",
                ai_response="test",
            )

        assert any(month in title for month in RUSSIAN_MONTHS)

    @pytest.mark.asyncio
    async def test_fallback_on_empty_response(self, naming_service):
        """Should fallback to date when LLM returns empty."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(return_value="")

        with patch.object(naming_service, "_llm", mock_llm):
            title = await naming_service.generate_session_title(
                user_message="test",
                ai_response="test",
            )

        assert any(month in title for month in RUSSIAN_MONTHS)

    @pytest.mark.asyncio
    async def test_fallback_on_short_response(self, naming_service):
        """Should fallback to date when LLM returns too short response."""
        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(return_value="X")

        with patch.object(naming_service, "_llm", mock_llm):
            title = await naming_service.generate_session_title(
                user_message="test",
                ai_response="test",
            )

        assert any(month in title for month in RUSSIAN_MONTHS)

    def test_date_fallback_format(self, naming_service):
        """Date fallback should be in format 'D месяца'."""
        # Test for February 3rd
        dt = datetime(2026, 2, 3)
        title = naming_service._generate_date_fallback(dt)
        assert title == "3 февраля"

        # Test for December 25th
        dt = datetime(2026, 12, 25)
        title = naming_service._generate_date_fallback(dt)
        assert title == "25 декабря"

    def test_date_fallback_uses_current_date_by_default(self, naming_service):
        """Date fallback should use current date when no date provided."""
        title = naming_service._generate_date_fallback()
        now = datetime.now()
        expected_month = RUSSIAN_MONTHS[now.month - 1]

        assert str(now.day) in title
        assert expected_month in title


class TestCleanTitle:
    """Tests for _clean_title helper."""

    def test_removes_various_quotes(self):
        """Should remove different types of quotes."""
        service = SessionNamingService()

        assert service._clean_title('"test"') == "test"
        assert service._clean_title("'test'") == "test"
        assert service._clean_title("«test»") == "test"
        # German quotation marks
        assert service._clean_title('\u201etest\u201c') == "test"

    def test_removes_extra_whitespace(self):
        """Should normalize whitespace."""
        service = SessionNamingService()

        assert service._clean_title("  test  title  ") == "test title"
        assert service._clean_title("test\n\ttitle") == "test title"

    def test_truncates_at_word_boundary(self):
        """Should prefer truncating at word boundary."""
        service = SessionNamingService()

        # This title is 35 chars, should be cut
        title = "Длинное название сессии вино стейк"
        result = service._clean_title(title)

        assert len(result) <= 30
        # Should not cut in the middle of a word
        assert not result.endswith("сте")

    def test_handles_empty_input(self):
        """Should handle empty input."""
        service = SessionNamingService()

        assert service._clean_title("") == ""
        assert service._clean_title(None) == ""
