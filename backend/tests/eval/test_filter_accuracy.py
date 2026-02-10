"""Eval: Verify LLM extracts correct filter values from natural language."""

import pytest

from app.services.sommelier_prompts import SYSTEM_PROMPT_AGENTIC

from tests.eval.golden_queries import FILTER_ACCURACY_QUERIES

pytestmark = [pytest.mark.eval, pytest.mark.asyncio]


@pytest.mark.parametrize(
    "gq",
    FILTER_ACCURACY_QUERIES,
    ids=lambda g: g.id,
)
async def test_filter_accuracy(sommelier_service, tool_spy, gq):
    """LLM should extract the expected filters from the query."""
    await sommelier_service.generate_agentic_response(
        system_prompt=SYSTEM_PROMPT_AGENTIC,
        user_message=gq.query_ru,
    )

    search_calls = tool_spy.search_calls()
    assert search_calls, (
        f"Expected search_wines call for: {gq.query_ru!r}\n"
        f"Got tools: {tool_spy.tool_names}"
    )

    actual = search_calls[0]

    for key, expected_val in gq.expected_filters.items():
        assert key in actual, (
            f"Missing filter '{key}' for query: {gq.query_ru!r}\n"
            f"Actual filters: {actual}"
        )

        actual_val = actual[key]

        if isinstance(expected_val, str) and isinstance(actual_val, str):
            # Case-insensitive partial match for string filters
            assert expected_val.lower() in actual_val.lower(), (
                f"Filter '{key}': expected '{expected_val}' in '{actual_val}'\n"
                f"Query: {gq.query_ru!r}"
            )
        elif isinstance(expected_val, (int, float)):
            # Numeric: allow 20% tolerance for price extraction
            tolerance = abs(expected_val) * 0.2
            assert abs(actual_val - expected_val) <= tolerance, (
                f"Filter '{key}': expected ~{expected_val}, got {actual_val}\n"
                f"Query: {gq.query_ru!r}"
            )
        else:
            assert actual_val == expected_val, (
                f"Filter '{key}': expected {expected_val!r}, got {actual_val!r}\n"
                f"Query: {gq.query_ru!r}"
            )
