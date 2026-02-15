"""Generate embeddings for wine seed data.

Usage:
    python -m app.scripts.generate_embeddings

Requires OPENROUTER_API_KEY environment variable.
Alternatively, set OPENAI_API_KEY to use OpenAI directly.
"""
import asyncio
import json
import os
from pathlib import Path

import openai


async def generate_embedding(client: openai.AsyncOpenAI, text: str, model: str) -> list[float]:
    """Generate embedding for text using OpenAI-compatible API."""
    response = await client.embeddings.create(
        model=model,
        input=text,
    )
    return response.data[0].embedding


def create_embedding_text(wine: dict) -> str:
    """Create text representation of wine for embedding."""
    parts = [
        f"{wine['name']} by {wine['producer']}",
        f"Type: {wine['wine_type']}",
        f"Country: {wine['country']}, Region: {wine['region']}",
        f"Grapes: {', '.join(wine['grape_varieties'])}",
        f"Sweetness: {wine['sweetness']}, Body: {wine['body']}/5",
        wine['description'],
    ]
    if wine.get('tasting_notes'):
        parts.append(f"Tasting notes: {wine['tasting_notes']}")
    if wine.get('food_pairings'):
        parts.append(f"Pairs with: {', '.join(wine['food_pairings'])}")
    return " ".join(parts)


async def main():
    """Generate embeddings for all wines in seed data."""
    # Check for OpenRouter first, then OpenAI
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if openrouter_key:
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        print(f"Using OpenRouter-compatible API ({base_url})")
        client = openai.AsyncOpenAI(
            api_key=openrouter_key,
            base_url=base_url,
        )
        embedding_model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    elif openai_key:
        print("Using OpenAI API directly")
        client = openai.AsyncOpenAI(api_key=openai_key)
        embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    else:
        print("Error: Set OPENROUTER_API_KEY or OPENAI_API_KEY environment variable")
        return

    # Load seed data
    seed_file = Path(__file__).parent.parent / "data" / "wines_seed.json"
    with open(seed_file) as f:
        data = json.load(f)

    print(f"Loaded {len(data['wines'])} wines from {seed_file}")
    print(f"Using embedding model: {embedding_model}")

    # Generate embeddings
    wines_with_embeddings = []
    for i, wine in enumerate(data["wines"]):
        text = create_embedding_text(wine)
        print(f"[{i+1}/{len(data['wines'])}] Generating embedding for: {wine['name'][:50]}...")

        try:
            embedding = await generate_embedding(client, text, embedding_model)
            wine_copy = wine.copy()
            wine_copy["embedding"] = embedding
            wines_with_embeddings.append(wine_copy)
        except Exception as e:
            print(f"  Error: {e}")
            wines_with_embeddings.append(wine)

    # Save output
    output_file = Path(__file__).parent.parent / "data" / "wines_seed_with_embeddings.json"
    with open(output_file, "w") as f:
        json.dump({"wines": wines_with_embeddings}, f, ensure_ascii=False)

    print(f"\nSaved {len(wines_with_embeddings)} wines to {output_file}")

    # Count wines with embeddings
    with_embeddings = sum(1 for w in wines_with_embeddings if "embedding" in w)
    print(f"Wines with embeddings: {with_embeddings}/{len(wines_with_embeddings)}")


if __name__ == "__main__":
    asyncio.run(main())
