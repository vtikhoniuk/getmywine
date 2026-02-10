"""Eval: Verify LLM selects the correct tool for each query type."""

import pytest

from app.services.sommelier_prompts import SYSTEM_PROMPT_AGENTIC

from tests.eval.golden_queries import TOOL_SELECTION_QUERIES

pytestmark = [pytest.mark.eval, pytest.mark.asyncio]


@pytest.mark.parametrize(
    "gq",
    TOOL_SELECTION_QUERIES,
    ids=lambda g: g.id,
)
async def test_tool_selection(sommelier_service, tool_spy, gq):
    """LLM should pick the expected tool for the given query."""
    await sommelier_service.generate_agentic_response(
        system_prompt=SYSTEM_PROMPT_AGENTIC,
        user_message=gq.query_ru,
    )

    assert tool_spy.calls, f"No tool calls made for: {gq.query_ru!r}"

    if gq.expected_tool != "any":
        assert tool_spy.first_tool == gq.expected_tool, (
            f"Query: {gq.query_ru!r}\n"
            f"Expected first tool: {gq.expected_tool}\n"
            f"Got: {tool_spy.first_tool}\n"
            f"All calls: {tool_spy.tool_names}"
        )
