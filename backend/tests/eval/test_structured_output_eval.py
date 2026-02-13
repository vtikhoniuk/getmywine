"""Eval: Verify LLM returns valid JSON matching SommelierResponse schema."""

import pytest

from app.services.sommelier_prompts import (
    SYSTEM_PROMPT_AGENTIC,
    SommelierResponse,
)

pytestmark = [pytest.mark.eval, pytest.mark.asyncio]

# Queries covering different response types
_STRUCTURED_OUTPUT_QUERIES = [
    # Recommendations (should produce wines)
    ("красное сухое до 3000 рублей", "recommendation"),
    ("белое к рыбе", "recommendation"),
    ("посоветуй вино к стейку", "recommendation"),
    # Informational (should produce no wines)
    ("что такое танины?", "informational"),
    ("расскажи про пино нуар как сорт", "informational"),
    # Off-topic / guard
    ("реши уравнение x^2=4", "off_topic"),
]


@pytest.mark.parametrize(
    "query,expected_type",
    _STRUCTURED_OUTPUT_QUERIES,
    ids=lambda x: x[:30] if isinstance(x, str) else x,
)
async def test_valid_structured_json(sommelier_service, query, expected_type):
    """LLM response must be valid JSON matching SommelierResponse schema."""
    result = await sommelier_service.generate_agentic_response(
        system_prompt=SYSTEM_PROMPT_AGENTIC,
        user_message=query,
    )

    assert result is not None, f"Agent returned None for: {query!r}"
    response_text, wine_ids = result

    # wine_ids should be a list (possibly empty)
    assert isinstance(wine_ids, list), (
        f"wine_ids should be list, got {type(wine_ids)}\n"
        f"Query: {query!r}"
    )

    if expected_type == "recommendation":
        # Should have wine IDs
        assert len(wine_ids) >= 1, (
            f"Expected wine_ids for recommendation query: {query!r}\n"
            f"Got: {wine_ids}"
        )
    elif expected_type == "informational":
        # Should have no wine IDs
        assert len(wine_ids) == 0, (
            f"Expected no wine_ids for informational query: {query!r}\n"
            f"Got: {wine_ids}"
        )


@pytest.mark.parametrize(
    "query",
    [q for q, _ in _STRUCTURED_OUTPUT_QUERIES[:3]],
    ids=lambda q: q[:30],
)
async def test_wine_ids_not_empty_strings(sommelier_service, query):
    """Wine IDs from structured output should not be empty strings."""
    result = await sommelier_service.generate_agentic_response(
        system_prompt=SYSTEM_PROMPT_AGENTIC,
        user_message=query,
    )

    assert result is not None
    _, wine_ids = result

    for wid in wine_ids:
        assert wid.strip(), f"Empty wine_id in response for: {query!r}"
