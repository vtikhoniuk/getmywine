"""Tests for the unified prompt system (SYSTEM_PROMPT_AGENTIC + build_unified_user_prompt).

T011: TDD Red phase — these tests should FAIL with ImportError until
SYSTEM_PROMPT_AGENTIC and build_unified_user_prompt are implemented
in app.services.sommelier_prompts.
"""

import pytest

from app.services.sommelier_prompts import (
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_AGENTIC,  # Will fail — doesn't exist yet
    build_unified_user_prompt,  # Will fail — doesn't exist yet
)


# ---------------------------------------------------------------------------
# 1. SYSTEM_PROMPT_AGENTIC — structure and content
# ---------------------------------------------------------------------------
class TestSystemPromptAgentic:
    """Tests verifying SYSTEM_PROMPT_AGENTIC structure and tool-related content."""

    def test_system_prompt_agentic_extends_base(self):
        """SYSTEM_PROMPT_AGENTIC must start with SYSTEM_PROMPT_BASE content."""
        assert SYSTEM_PROMPT_AGENTIC.startswith(SYSTEM_PROMPT_BASE)

    def test_system_prompt_agentic_contains_tool_instructions(self):
        """SYSTEM_PROMPT_AGENTIC must mention tool names and usage keywords."""
        prompt_lower = SYSTEM_PROMPT_AGENTIC.lower()
        assert "search_wines" in prompt_lower, (
            "SYSTEM_PROMPT_AGENTIC should reference 'search_wines' tool"
        )
        assert "semantic_search" in prompt_lower, (
            "SYSTEM_PROMPT_AGENTIC should reference 'semantic_search' tool"
        )
        assert "инструмент" in prompt_lower, (
            "SYSTEM_PROMPT_AGENTIC should mention 'инструмент' (tool in Russian)"
        )

    def test_system_prompt_agentic_longer_than_base(self):
        """SYSTEM_PROMPT_AGENTIC must contain additional content beyond SYSTEM_PROMPT_BASE."""
        assert len(SYSTEM_PROMPT_AGENTIC) > len(SYSTEM_PROMPT_BASE)


# ---------------------------------------------------------------------------
# 2. build_unified_user_prompt — with user profile
# ---------------------------------------------------------------------------
class TestBuildUnifiedUserPromptWithProfile:
    """Tests for build_unified_user_prompt when user_profile is provided."""

    def test_build_unified_user_prompt_with_profile(self):
        """Output should contain formatted profile information."""
        profile = {
            "sweetness_pref": "сухое",
            "body_pref": "полнотелое",
            "favorite_regions": ["Бордо", "Тоскана"],
            "dislikes": ["сладкое"],
            "budget": "до 3000 руб.",
        }
        result = build_unified_user_prompt(
            user_message="Посоветуй вино к стейку",
            user_profile=profile,
        )

        assert "сухое" in result
        assert "полнотелое" in result
        assert "Бордо" in result

    def test_build_unified_user_prompt_with_partial_profile(self):
        """Output should handle a partially filled profile (only some keys)."""
        profile = {
            "sweetness_pref": "полусухое",
        }
        result = build_unified_user_prompt(
            user_message="Что попить вечером?",
            user_profile=profile,
        )

        assert "полусухое" in result
        assert "Что попить вечером?" in result


# ---------------------------------------------------------------------------
# 3. build_unified_user_prompt — with events context
# ---------------------------------------------------------------------------
class TestBuildUnifiedUserPromptWithEvents:
    """Tests for build_unified_user_prompt when events_context is provided."""

    def test_build_unified_user_prompt_with_events(self):
        """Output should include the events/holidays context string."""
        events = "Ближайший праздник: 8 Марта (через 5 дней)"
        result = build_unified_user_prompt(
            user_message="Подбери вино на праздник",
            events_context=events,
        )

        assert events in result

    def test_build_unified_user_prompt_with_profile_and_events(self):
        """Output should include both profile and events when both provided."""
        profile = {
            "sweetness_pref": "сухое",
            "favorite_regions": ["Риоха"],
        }
        events = "Сезон: зима. Ближайший праздник: Новый год (через 10 дней)"
        result = build_unified_user_prompt(
            user_message="Вино для новогоднего стола",
            user_profile=profile,
            events_context=events,
        )

        assert "сухое" in result
        assert "Риоха" in result
        assert "Новый год" in result
        assert "Вино для новогоднего стола" in result


# ---------------------------------------------------------------------------
# 4. build_unified_user_prompt — cold start (no profile, no events)
# ---------------------------------------------------------------------------
class TestBuildUnifiedUserPromptColdStart:
    """Tests for build_unified_user_prompt without profile or events (cold start)."""

    def test_build_unified_user_prompt_cold_start(self):
        """Should work without profile or events and still include the user message."""
        result = build_unified_user_prompt(user_message="Привет, посоветуй вино")

        assert isinstance(result, str)
        assert len(result) > 0
        assert "Привет, посоветуй вино" in result

    def test_build_unified_user_prompt_cold_start_no_crash_on_none(self):
        """Explicitly passing None for optional args should not raise."""
        result = build_unified_user_prompt(
            user_message="Хочу красное вино",
            user_profile=None,
            events_context=None,
        )

        assert "Хочу красное вино" in result


# ---------------------------------------------------------------------------
# 5. build_unified_user_prompt — user message always present
# ---------------------------------------------------------------------------
class TestBuildUnifiedUserPromptIncludesMessage:
    """Tests verifying the user's original message is always in the output."""

    def test_build_unified_user_prompt_includes_user_message(self):
        """The user's message must appear verbatim in the output."""
        message = "Ищу вино с нотами вишни и шоколада до 2000 рублей"
        result = build_unified_user_prompt(user_message=message)

        assert message in result

    def test_build_unified_user_prompt_includes_message_with_all_context(self):
        """User message must be present even when profile and events are provided."""
        message = "Порекомендуй что-нибудь интересное"
        profile = {"sweetness_pref": "сухое"}
        events = "Сезон: лето"

        result = build_unified_user_prompt(
            user_message=message,
            user_profile=profile,
            events_context=events,
        )

        assert message in result
