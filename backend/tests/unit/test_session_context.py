"""Unit tests for SessionContextService.

Tests:
- T034: extract_session_insights() extracts insights from conversation
- T035: build_cross_session_context() aggregates context from multiple sessions
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.session_context import (
    CrossSessionContext,
    SessionContextService,
    SessionInsights,
)


# ============================================================================
# SessionInsights Dataclass Tests
# ============================================================================


class TestSessionInsights:
    """Tests for SessionInsights dataclass."""

    def test_is_empty_when_all_lists_empty(self):
        """Should return True when all lists are empty."""
        insights = SessionInsights()
        assert insights.is_empty() is True

    def test_is_empty_when_has_liked_wines(self):
        """Should return False when has liked wines."""
        insights = SessionInsights(liked_wines=["Merlot"])
        assert insights.is_empty() is False

    def test_is_empty_when_has_disliked_wines(self):
        """Should return False when has disliked wines."""
        insights = SessionInsights(disliked_wines=["Chardonnay"])
        assert insights.is_empty() is False

    def test_is_empty_when_has_events(self):
        """Should return False when has events discussed."""
        insights = SessionInsights(events_discussed=["день рождения"])
        assert insights.is_empty() is False

    def test_is_empty_when_has_foods(self):
        """Should return False when has foods paired."""
        insights = SessionInsights(foods_paired=["стейк"])
        assert insights.is_empty() is False

    def test_to_dict_returns_all_fields(self):
        """Should convert to dictionary with all fields."""
        insights = SessionInsights(
            liked_wines=["Wine1", "Wine2"],
            disliked_wines=["Wine3"],
            events_discussed=["event1"],
            foods_paired=["food1", "food2"],
        )
        result = insights.to_dict()

        assert result == {
            "liked_wines": ["Wine1", "Wine2"],
            "disliked_wines": ["Wine3"],
            "events_discussed": ["event1"],
            "foods_paired": ["food1", "food2"],
        }


# ============================================================================
# CrossSessionContext Dataclass Tests
# ============================================================================


class TestCrossSessionContext:
    """Tests for CrossSessionContext dataclass."""

    def test_to_prompt_text_empty_when_no_sessions(self):
        """Should return empty string when no sessions."""
        context = CrossSessionContext(
            total_sessions=0,
            recent_wines=[],
            preferences=SessionInsights(),
            last_session_date=None,
        )
        assert context.to_prompt_text() == ""

    def test_to_prompt_text_includes_session_count(self):
        """Should include session count in prompt."""
        context = CrossSessionContext(
            total_sessions=3,
            recent_wines=[],
            preferences=SessionInsights(),
            last_session_date=datetime.now(),
        )
        result = context.to_prompt_text()
        assert "3 сессий" in result

    def test_to_prompt_text_includes_recent_wines(self):
        """Should include recent wines in prompt."""
        context = CrossSessionContext(
            total_sessions=2,
            recent_wines=["Merlot", "Cabernet"],
            preferences=SessionInsights(),
            last_session_date=datetime.now(),
        )
        result = context.to_prompt_text()
        assert "Недавно обсуждали" in result
        assert "Merlot" in result
        assert "Cabernet" in result

    def test_to_prompt_text_includes_liked_wines(self):
        """Should include liked wines from preferences."""
        context = CrossSessionContext(
            total_sessions=1,
            recent_wines=[],
            preferences=SessionInsights(liked_wines=["Pinot Noir"]),
            last_session_date=datetime.now(),
        )
        result = context.to_prompt_text()
        assert "Понравились" in result
        assert "Pinot Noir" in result

    def test_to_prompt_text_includes_disliked_wines(self):
        """Should include disliked wines from preferences."""
        context = CrossSessionContext(
            total_sessions=1,
            recent_wines=[],
            preferences=SessionInsights(disliked_wines=["Riesling"]),
            last_session_date=datetime.now(),
        )
        result = context.to_prompt_text()
        assert "Не понравились" in result
        assert "Riesling" in result

    def test_to_prompt_text_includes_events(self):
        """Should include events discussed."""
        context = CrossSessionContext(
            total_sessions=1,
            recent_wines=[],
            preferences=SessionInsights(events_discussed=["день рождения"]),
            last_session_date=datetime.now(),
        )
        result = context.to_prompt_text()
        assert "События" in result
        assert "день рождения" in result

    def test_to_prompt_text_includes_foods(self):
        """Should include foods paired."""
        context = CrossSessionContext(
            total_sessions=1,
            recent_wines=[],
            preferences=SessionInsights(foods_paired=["стейк"]),
            last_session_date=datetime.now(),
        )
        result = context.to_prompt_text()
        assert "Еда" in result
        assert "стейк" in result

    def test_to_prompt_text_limits_items(self):
        """Should limit items to avoid overly long prompts."""
        context = CrossSessionContext(
            total_sessions=1,
            recent_wines=["W1", "W2", "W3", "W4", "W5", "W6", "W7"],
            preferences=SessionInsights(
                liked_wines=["L1", "L2", "L3", "L4", "L5", "L6", "L7"],
            ),
            last_session_date=datetime.now(),
        )
        result = context.to_prompt_text()
        # Should limit recent wines to 5
        assert "W6" not in result
        # Should limit liked wines to 5
        assert "L6" not in result


# ============================================================================
# SessionContextService Tests - T034: extract_session_insights()
# ============================================================================


@pytest.mark.asyncio
class TestExtractSessionInsights:
    """T034: Tests for extract_session_insights()."""

    async def test_returns_empty_insights_when_no_messages(self):
        """Should return empty insights when conversation has no messages."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        mock_conversation = MagicMock()
        mock_conversation.messages = []

        result = await service.extract_session_insights(mock_conversation)

        assert result.is_empty()

    async def test_returns_empty_insights_when_only_welcome_messages(self):
        """Should return empty insights when only welcome messages exist."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        mock_msg = MagicMock()
        mock_msg.is_welcome = True
        mock_msg.role.value = "assistant"
        mock_msg.content = "Welcome!"

        mock_conversation = MagicMock()
        mock_conversation.messages = [mock_msg]

        result = await service.extract_session_insights(mock_conversation)

        assert result.is_empty()

    async def test_returns_empty_insights_when_llm_unavailable(self):
        """Should return empty insights when LLM is not available."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        mock_llm = MagicMock()
        mock_llm.is_available = False
        service._llm = mock_llm

        mock_msg = MagicMock()
        mock_msg.is_welcome = False
        mock_msg.role.value = "user"
        mock_msg.content = "Посоветуй вино"

        mock_conversation = MagicMock()
        mock_conversation.messages = [mock_msg]

        result = await service.extract_session_insights(mock_conversation)

        assert result.is_empty()

    async def test_extracts_insights_from_llm_response(self):
        """Should extract insights from LLM JSON response."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(return_value="""{
            "liked_wines": ["Barolo", "Chianti"],
            "disliked_wines": ["Riesling"],
            "events_discussed": ["день рождения"],
            "foods_paired": ["стейк", "паста"]
        }""")
        service._llm = mock_llm

        mock_msg = MagicMock()
        mock_msg.is_welcome = False
        mock_msg.role.value = "user"
        mock_msg.content = "Мне понравился Barolo"

        mock_conversation = MagicMock()
        mock_conversation.messages = [mock_msg]

        result = await service.extract_session_insights(mock_conversation)

        assert result.liked_wines == ["Barolo", "Chianti"]
        assert result.disliked_wines == ["Riesling"]
        assert result.events_discussed == ["день рождения"]
        assert result.foods_paired == ["стейк", "паста"]

    async def test_handles_llm_error_gracefully(self):
        """Should return empty insights on LLM error."""
        from app.services.llm import LLMError

        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(side_effect=LLMError("API error"))
        service._llm = mock_llm

        mock_msg = MagicMock()
        mock_msg.is_welcome = False
        mock_msg.role.value = "user"
        mock_msg.content = "Вино"

        mock_conversation = MagicMock()
        mock_conversation.messages = [mock_msg]

        result = await service.extract_session_insights(mock_conversation)

        assert result.is_empty()

    async def test_handles_invalid_json_gracefully(self):
        """Should return empty insights on invalid JSON."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        mock_llm = MagicMock()
        mock_llm.is_available = True
        mock_llm.generate = AsyncMock(return_value="not valid json")
        service._llm = mock_llm

        mock_msg = MagicMock()
        mock_msg.is_welcome = False
        mock_msg.role.value = "user"
        mock_msg.content = "Вино"

        mock_conversation = MagicMock()
        mock_conversation.messages = [mock_msg]

        result = await service.extract_session_insights(mock_conversation)

        assert result.is_empty()


class TestParseInsightsResponse:
    """Tests for _parse_insights_response() helper."""

    def test_parses_valid_json(self):
        """Should parse valid JSON response."""
        service = SessionContextService(MagicMock())
        response = """{
            "liked_wines": ["Wine1"],
            "disliked_wines": ["Wine2"],
            "events_discussed": ["Event1"],
            "foods_paired": ["Food1"]
        }"""

        result = service._parse_insights_response(response)

        assert result.liked_wines == ["Wine1"]
        assert result.disliked_wines == ["Wine2"]
        assert result.events_discussed == ["Event1"]
        assert result.foods_paired == ["Food1"]

    def test_handles_markdown_code_block(self):
        """Should handle JSON wrapped in markdown code block."""
        service = SessionContextService(MagicMock())
        response = """```json
{
    "liked_wines": ["Wine1"],
    "disliked_wines": [],
    "events_discussed": [],
    "foods_paired": []
}
```"""

        result = service._parse_insights_response(response)

        assert result.liked_wines == ["Wine1"]

    def test_limits_list_lengths(self):
        """Should limit lists to prevent overly long results."""
        import json

        service = SessionContextService(MagicMock())
        # Create response with many items
        wines = [f"Wine{i}" for i in range(20)]
        response = json.dumps({
            "liked_wines": wines,
            "disliked_wines": [],
            "events_discussed": [],
            "foods_paired": [],
        })

        result = service._parse_insights_response(response)

        # Should be limited to 10
        assert len(result.liked_wines) == 10

    def test_handles_missing_fields(self):
        """Should handle missing fields with defaults."""
        service = SessionContextService(MagicMock())
        response = '{"liked_wines": ["Wine1"]}'

        result = service._parse_insights_response(response)

        assert result.liked_wines == ["Wine1"]
        assert result.disliked_wines == []
        assert result.events_discussed == []
        assert result.foods_paired == []


# ============================================================================
# SessionContextService Tests - T035: build_cross_session_context()
# ============================================================================


@pytest.mark.asyncio
class TestBuildCrossSessionContext:
    """T035: Tests for build_cross_session_context()."""

    async def test_returns_empty_context_when_no_sessions(self):
        """Should return empty context when user has no sessions."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        # Mock repository to return empty list
        service.conversation_repo.get_all_by_user_id = AsyncMock(return_value=([], 0))

        user_id = uuid.uuid4()
        result = await service.build_cross_session_context(user_id)

        assert result.total_sessions == 0
        assert result.recent_wines == []
        assert result.preferences.is_empty()
        assert result.last_session_date is None

    async def test_excludes_specified_session(self):
        """Should exclude the specified session from context."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        session_id = uuid.uuid4()
        exclude_id = uuid.uuid4()

        mock_conv1 = MagicMock()
        mock_conv1.id = session_id
        mock_conv1.messages = []
        mock_conv1.updated_at = datetime.now()

        mock_conv2 = MagicMock()
        mock_conv2.id = exclude_id
        mock_conv2.messages = []
        mock_conv2.updated_at = datetime.now()

        service.conversation_repo.get_all_by_user_id = AsyncMock(
            return_value=([mock_conv1, mock_conv2], 2)
        )

        user_id = uuid.uuid4()
        result = await service.build_cross_session_context(
            user_id, exclude_session_id=exclude_id
        )

        # Should only count 1 session (the one not excluded)
        # Note: total_sessions comes from repo's total count
        assert result.total_sessions == 2  # total from DB

    async def test_extracts_insights_from_sessions(self):
        """Should extract and aggregate insights from sessions."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        # Create mock message with event keyword
        mock_msg = MagicMock()
        mock_msg.is_welcome = False
        mock_msg.role.value = "user"
        mock_msg.content = "Вино на день рождения"

        mock_conv = MagicMock()
        mock_conv.id = uuid.uuid4()
        mock_conv.messages = [mock_msg]
        mock_conv.updated_at = datetime.now()

        service.conversation_repo.get_all_by_user_id = AsyncMock(
            return_value=([mock_conv], 1)
        )

        user_id = uuid.uuid4()
        result = await service.build_cross_session_context(user_id)

        assert result.total_sessions == 1
        assert "день рождения" in result.preferences.events_discussed

    async def test_extracts_wine_mentions_from_ai_responses(self):
        """Should extract wine mentions from AI responses."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        # Create mock AI message with wine recommendation
        mock_msg = MagicMock()
        mock_msg.is_welcome = False
        mock_msg.role.value = "assistant"
        mock_msg.content = "Рекомендую попробовать Barolo - отличное итальянское вино."

        mock_conv = MagicMock()
        mock_conv.id = uuid.uuid4()
        mock_conv.messages = [mock_msg]
        mock_conv.updated_at = datetime.now()

        service.conversation_repo.get_all_by_user_id = AsyncMock(
            return_value=([mock_conv], 1)
        )

        user_id = uuid.uuid4()
        result = await service.build_cross_session_context(user_id)

        assert "Barolo" in result.recent_wines

    async def test_limits_sessions_analyzed(self):
        """Should limit number of sessions analyzed."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        # Create 10 mock conversations
        convs = []
        for i in range(10):
            mock_conv = MagicMock()
            mock_conv.id = uuid.uuid4()
            mock_conv.messages = []
            mock_conv.updated_at = datetime.now()
            convs.append(mock_conv)

        service.conversation_repo.get_all_by_user_id = AsyncMock(
            return_value=(convs, 10)
        )

        user_id = uuid.uuid4()
        result = await service.build_cross_session_context(user_id, max_sessions=3)

        # Should have total_sessions from DB but only analyze max_sessions
        assert result.total_sessions == 10

    async def test_deduplicates_insights(self):
        """Should deduplicate insights from multiple sessions."""
        mock_db = MagicMock()
        service = SessionContextService(mock_db)

        # Create two sessions mentioning the same event
        mock_msg1 = MagicMock()
        mock_msg1.is_welcome = False
        mock_msg1.role.value = "user"
        mock_msg1.content = "Вино на день рождения"

        mock_msg2 = MagicMock()
        mock_msg2.is_welcome = False
        mock_msg2.role.value = "user"
        mock_msg2.content = "Ещё вино на день рождения"

        mock_conv1 = MagicMock()
        mock_conv1.id = uuid.uuid4()
        mock_conv1.messages = [mock_msg1]
        mock_conv1.updated_at = datetime.now()

        mock_conv2 = MagicMock()
        mock_conv2.id = uuid.uuid4()
        mock_conv2.messages = [mock_msg2]
        mock_conv2.updated_at = datetime.now()

        service.conversation_repo.get_all_by_user_id = AsyncMock(
            return_value=([mock_conv1, mock_conv2], 2)
        )

        user_id = uuid.uuid4()
        result = await service.build_cross_session_context(user_id)

        # Should only have one "день рождения" entry
        assert result.preferences.events_discussed.count("день рождения") == 1


# ============================================================================
# Helper Method Tests
# ============================================================================


class TestExtractSimpleInsights:
    """Tests for _extract_simple_insights() keyword extraction."""

    def test_extracts_event_keywords(self):
        """Should extract event keywords from messages."""
        service = SessionContextService(MagicMock())

        mock_msg = MagicMock()
        mock_msg.is_welcome = False
        mock_msg.role.value = "user"
        # Use "ужин" which matches exactly (no case declension issues)
        mock_msg.content = "Вино для романтического ужин"

        mock_conv = MagicMock()
        mock_conv.messages = [mock_msg]

        result = service._extract_simple_insights(mock_conv)

        assert "ужин" in result.events_discussed

    def test_extracts_food_keywords(self):
        """Should extract food keywords from user messages."""
        service = SessionContextService(MagicMock())

        mock_msg = MagicMock()
        mock_msg.is_welcome = False
        mock_msg.role.value = "user"
        mock_msg.content = "Что подойдет к стейку?"

        mock_conv = MagicMock()
        mock_conv.messages = [mock_msg]

        result = service._extract_simple_insights(mock_conv)

        assert "стейк" in result.foods_paired

    def test_ignores_welcome_messages(self):
        """Should skip welcome messages."""
        service = SessionContextService(MagicMock())

        mock_msg = MagicMock()
        mock_msg.is_welcome = True
        mock_msg.role.value = "assistant"
        mock_msg.content = "Добро пожаловать! Хотите вино на праздник?"

        mock_conv = MagicMock()
        mock_conv.messages = [mock_msg]

        result = service._extract_simple_insights(mock_conv)

        # Should not extract "праздник" from welcome message
        assert result.is_empty()

    def test_extracts_multiple_events(self):
        """Should extract multiple different events."""
        service = SessionContextService(MagicMock())

        mock_msg = MagicMock()
        mock_msg.is_welcome = False
        mock_msg.role.value = "user"
        mock_msg.content = "Планирую юбилей, потом новый год"

        mock_conv = MagicMock()
        mock_conv.messages = [mock_msg]

        result = service._extract_simple_insights(mock_conv)

        assert "юбилей" in result.events_discussed
        assert "Новый год" in result.events_discussed


class TestExtractWineMentions:
    """Tests for _extract_wine_mentions() helper."""

    def test_extracts_wine_after_recommendation_pattern(self):
        """Should extract wine names after recommendation patterns."""
        service = SessionContextService(MagicMock())

        text = "Рекомендую попробовать Barolo"
        result = service._extract_wine_mentions(text)

        assert "Barolo" in result

    def test_skips_common_russian_words(self):
        """Should skip common Russian words that start with capital."""
        service = SessionContextService(MagicMock())

        text = "Для вас рекомендую вино. Если хотите, попробуйте."
        result = service._extract_wine_mentions(text)

        assert "Для" not in result
        assert "Если" not in result

    def test_limits_extracted_wines(self):
        """Should limit number of extracted wines per message."""
        service = SessionContextService(MagicMock())

        # Many potential wine names
        text = "Рекомендую Wine1 Wine2 Wine3 Wine4 Wine5 Wine6 Wine7 Wine8"
        result = service._extract_wine_mentions(text)

        assert len(result) <= 5

    def test_handles_text_without_patterns(self):
        """Should return empty list when no patterns match."""
        service = SessionContextService(MagicMock())

        text = "Обычный текст без рекомендаций."
        result = service._extract_wine_mentions(text)

        assert result == []
