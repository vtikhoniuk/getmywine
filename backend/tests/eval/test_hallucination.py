"""Eval: Verify LLM does not hallucinate wines outside the catalog."""

import re

import pytest

from app.services.sommelier_prompts import (
    SYSTEM_PROMPT_AGENTIC,
    parse_structured_response,
)

pytestmark = [pytest.mark.eval, pytest.mark.asyncio]

# Queries that should produce wine recommendations
_HALLUCINATION_QUERIES = [
    "красное сухое до 3000 рублей",
    "белое к рыбе",
    "что-нибудь из Италии",
]


@pytest.mark.parametrize("query", _HALLUCINATION_QUERIES, ids=lambda q: q[:30])
async def test_no_hallucinated_wines(sommelier_service, catalog_wines, query):
    """Every wine mentioned in the response must exist in the catalog."""
    response = await sommelier_service.generate_agentic_response(
        system_prompt=SYSTEM_PROMPT_AGENTIC,
        user_message=query,
    )

    assert response is not None, f"Agent returned None for: {query!r}"

    parsed = parse_structured_response(response)
    if not parsed.wines:
        # No wine sections found — nothing to validate
        pytest.skip("No wine sections in response")

    # Build catalog name set (lowered for fuzzy matching)
    catalog_names = {w.name.lower() for w in catalog_wines}

    for i, wine_text in enumerate(parsed.wines, 1):
        # First line of wine section is the name (possibly in bold)
        first_line = wine_text.split("\n")[0].strip()
        # Strip markdown bold markers
        first_line = re.sub(r"\*\*(.+?)\*\*", r"\1", first_line)

        # Check that at least one catalog wine name appears in the first line
        found = any(
            catalog_name in first_line.lower() for catalog_name in catalog_names
        )
        assert found, (
            f"WINE:{i} may be hallucinated.\n"
            f"First line: {first_line!r}\n"
            f"Query: {query!r}\n"
            f"Catalog has {len(catalog_names)} wines."
        )
