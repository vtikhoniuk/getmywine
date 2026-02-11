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
    response_text, wine_names = result

    # wine_names should be a list (possibly empty)
    assert isinstance(wine_names, list), (
        f"wine_names should be list, got {type(wine_names)}\n"
        f"Query: {query!r}"
    )

    if expected_type == "recommendation":
        # Should have wine names
        assert len(wine_names) >= 1, (
            f"Expected wine_names for recommendation query: {query!r}\n"
            f"Got: {wine_names}"
        )
    elif expected_type == "informational":
        # Should have no wine names
        assert len(wine_names) == 0, (
            f"Expected no wine_names for informational query: {query!r}\n"
            f"Got: {wine_names}"
        )


@pytest.mark.parametrize(
    "query",
    [q for q, _ in _STRUCTURED_OUTPUT_QUERIES[:3]],
    ids=lambda q: q[:30],
)
async def test_wine_names_not_empty_strings(sommelier_service, query):
    """Wine names from structured output should not be empty strings."""
    result = await sommelier_service.generate_agentic_response(
        system_prompt=SYSTEM_PROMPT_AGENTIC,
        user_message=query,
    )

    assert result is not None
    _, wine_names = result

    for name in wine_names:
        assert name.strip(), f"Empty wine_name in response for: {query!r}"
