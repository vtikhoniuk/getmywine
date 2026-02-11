"""Eval: Verify semantic search returns relevant results."""

import pytest

from app.services.llm import get_llm_service
from app.repositories.wine import WineRepository

from tests.eval.golden_queries import SEMANTIC_QUERIES

pytestmark = [pytest.mark.eval, pytest.mark.asyncio]

# Minimum cosine similarity to consider a result relevant
_MIN_SIMILARITY = 0.15


@pytest.mark.parametrize(
    "gq",
    SEMANTIC_QUERIES,
    ids=lambda g: g.id,
)
async def test_semantic_search_relevance(eval_db, gq):
    """Semantic search should return results above minimum similarity."""
    llm = get_llm_service()
    repo = WineRepository(eval_db)

    embedding = await llm.get_query_embedding(gq.query_ru)
    results = await repo.semantic_search(embedding=embedding, limit=5)

    assert len(results) >= gq.min_results, (
        f"Expected >= {gq.min_results} results for: {gq.query_ru!r}\n"
        f"Got: {len(results)}"
    )

    for wine, score in results:
        assert score > _MIN_SIMILARITY, (
            f"Low similarity {score:.3f} for '{wine.name}'\n"
            f"Query: {gq.query_ru!r}"
        )


async def test_semantic_search_ordering(eval_db):
    """Results should be ordered by descending similarity score."""
    llm = get_llm_service()
    repo = WineRepository(eval_db)

    embedding = await llm.get_query_embedding("лёгкое фруктовое белое вино")
    results = await repo.semantic_search(embedding=embedding, limit=5)

    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True), (
        f"Results not ordered by similarity: {scores}"
    )


async def test_semantic_vs_structured_differentiation(eval_db):
    """Semantic search for 'berry notes' should return different wines
    than semantic search for 'mineral crisp white'."""
    llm = get_llm_service()
    repo = WineRepository(eval_db)

    emb_berry = await llm.get_query_embedding("вино с ягодными нотами")
    emb_mineral = await llm.get_query_embedding("минеральное хрустящее белое")

    results_berry = await repo.semantic_search(embedding=emb_berry, limit=3)
    results_mineral = await repo.semantic_search(embedding=emb_mineral, limit=3)

    names_berry = {w.name for w, _ in results_berry}
    names_mineral = {w.name for w, _ in results_mineral}

    # At least one result should differ between the two queries
    assert names_berry != names_mineral, (
        "Semantic search returned identical results for very different queries.\n"
        f"Berry: {names_berry}\n"
        f"Mineral: {names_mineral}"
    )
