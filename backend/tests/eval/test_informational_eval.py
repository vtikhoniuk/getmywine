"""Eval: Verify expanded informational responses for wine-adjacent topics.

Tests cover:
- T001: Informational response has intro >= 3 sentences
- T002: Closing contains thematic wine-related segue
- T003: 3 consecutive questions produce different closings
- T004: Regression — recommendation queries still work
"""

import re

import pytest

from app.services.sommelier_prompts import SYSTEM_PROMPT_AGENTIC

pytestmark = [pytest.mark.eval, pytest.mark.asyncio]


def _count_sentences(text: str) -> int:
    """Count sentences in text using sentence-ending punctuation."""
    # Split on sentence-ending punctuation followed by space or end-of-string
    sentences = re.split(r'[.!?]+(?:\s|$)', text.strip())
    # Filter out empty strings from split
    return len([s for s in sentences if s.strip()])


def _extract_intro_and_closing(rendered_text: str) -> tuple[str, str]:
    """Split rendered response into intro and closing parts.

    For informational responses (no wines), rendered text is:
    intro + "\\n\\n" + closing
    """
    parts = rendered_text.split("\n\n")
    if len(parts) >= 2:
        # Last paragraph is closing, everything else is intro
        closing = parts[-1]
        intro = "\n\n".join(parts[:-1])
        return intro, closing
    return rendered_text, ""


# Wine-adjacent queries (not about specific wines)
_INFORMATIONAL_QUERIES = [
    "Расскажи про Бордо как винный регион",
    "Что такое малолактическая ферментация?",
    "Чем отличается органическое виноделие от обычного?",
]


# --- T001: Informational response has intro >= 3 sentences ---


@pytest.mark.parametrize(
    "query",
    _INFORMATIONAL_QUERIES,
    ids=lambda q: q[:40],
)
async def test_informational_intro_length(sommelier_service, query):
    """Informational response intro must contain at least 3 sentences (FR-002)."""
    result = await sommelier_service.generate_agentic_response(
        system_prompt=SYSTEM_PROMPT_AGENTIC,
        user_message=query,
    )

    assert result is not None, f"Agent returned None for: {query!r}"
    response_text, wine_names = result

    # Should be informational (no wines)
    assert len(wine_names) == 0, (
        f"Expected no wines for informational query: {query!r}\n"
        f"Got wine_names: {wine_names}"
    )

    intro, _ = _extract_intro_and_closing(response_text)
    sentence_count = _count_sentences(intro)

    assert sentence_count >= 3, (
        f"Informational intro should have >= 3 sentences, got {sentence_count}\n"
        f"Query: {query!r}\n"
        f"Intro: {intro!r}"
    )


# --- T002: Closing contains thematic wine-related segue ---


# Words that indicate the closing references specific wines (not generic)
_WINE_TOPIC_INDICATORS = [
    "вин", "вино", "бутылк", "попробов", "продегустир", "подобр",
    "порекоменд", "посоветов", "обсуд", "рассказ",
]


@pytest.mark.parametrize(
    "query",
    _INFORMATIONAL_QUERIES,
    ids=lambda q: q[:40],
)
async def test_informational_closing_has_wine_segue(sommelier_service, query):
    """Informational closing must contain a thematic segue to wine discussion (FR-003)."""
    result = await sommelier_service.generate_agentic_response(
        system_prompt=SYSTEM_PROMPT_AGENTIC,
        user_message=query,
    )

    assert result is not None, f"Agent returned None for: {query!r}"
    response_text, _ = result

    _, closing = _extract_intro_and_closing(response_text)

    assert closing, (
        f"Informational response should have a closing/segue\n"
        f"Query: {query!r}\n"
        f"Full response: {response_text!r}"
    )

    closing_lower = closing.lower()
    has_wine_reference = any(
        indicator in closing_lower for indicator in _WINE_TOPIC_INDICATORS
    )

    assert has_wine_reference, (
        f"Closing should reference wines thematically\n"
        f"Query: {query!r}\n"
        f"Closing: {closing!r}"
    )


# --- T003: 3 consecutive questions produce different closings ---


async def test_informational_closing_variety(sommelier_service):
    """3 consecutive informational questions must produce different closings (FR-004, SC-003)."""
    closings = []

    for query in _INFORMATIONAL_QUERIES:
        result = await sommelier_service.generate_agentic_response(
            system_prompt=SYSTEM_PROMPT_AGENTIC,
            user_message=query,
        )

        assert result is not None, f"Agent returned None for: {query!r}"
        response_text, _ = result

        _, closing = _extract_intro_and_closing(response_text)
        closings.append(closing)

    # All 3 closings must be different
    assert len(set(closings)) == 3, (
        f"Expected 3 different closings, got {len(set(closings))} unique\n"
        f"Closings:\n"
        + "\n".join(f"  [{i+1}] {c!r}" for i, c in enumerate(closings))
    )


# --- T004: Regression — recommendation queries still work ---


_RECOMMENDATION_QUERIES = [
    "посоветуй красное сухое до 2000 рублей",
    "белое вино к рыбе",
]


@pytest.mark.parametrize(
    "query",
    _RECOMMENDATION_QUERIES,
    ids=lambda q: q[:40],
)
async def test_recommendation_regression(sommelier_service, query):
    """Recommendation queries must still return wines (SC-004 regression check)."""
    result = await sommelier_service.generate_agentic_response(
        system_prompt=SYSTEM_PROMPT_AGENTIC,
        user_message=query,
    )

    assert result is not None, f"Agent returned None for: {query!r}"
    _, wine_names = result

    assert len(wine_names) >= 1, (
        f"Expected wine_names for recommendation query: {query!r}\n"
        f"Got: {wine_names}"
    )
