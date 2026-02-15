"""Seed wines table with 50 wines

Revision ID: 006
Revises: 005
Create Date: 2026-02-03

Generates embeddings on-the-fly using OpenRouter or OpenAI API.
Set OPENROUTER_API_KEY or OPENAI_API_KEY environment variable.
"""
import json
import os
import time
import uuid
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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


def generate_embedding(text: str, api_key: str, base_url: str, model: str) -> list[float] | None:
    """Generate embedding using OpenAI-compatible API."""
    import requests

    try:
        response = requests.post(
            f"{base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": text,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]
    except Exception as e:
        print(f"    Error generating embedding: {e}")
        return None


def upgrade() -> None:
    # Check for API keys
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    api_key = None
    base_url = None
    model = None

    if openrouter_key:
        print("Using OpenRouter-compatible API for embeddings")
        api_key = openrouter_key
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    elif openai_key:
        print("Using OpenAI API for embeddings")
        api_key = openai_key
        base_url = "https://api.openai.com/v1"
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    else:
        print("WARNING: No API key found. Wines will be seeded WITHOUT embeddings.")
        print("Set OPENROUTER_API_KEY or OPENAI_API_KEY to enable semantic search.")

    # Load seed data
    data_dir = Path(__file__).parent.parent.parent / "app" / "data"
    seed_file = data_dir / "wines_seed.json"

    with open(seed_file) as f:
        data = json.load(f)

    total = len(data["wines"])
    print(f"Seeding {total} wines...")

    # Insert wines
    for i, wine in enumerate(data["wines"]):
        wine_id = str(uuid.uuid4())

        # Generate embedding if API key available
        embedding_value = "NULL"
        if api_key:
            text = create_embedding_text(wine)
            print(f"  [{i+1}/{total}] {wine['name'][:40]}... ", end="", flush=True)

            embedding = generate_embedding(text, api_key, base_url, model)
            if embedding:
                embedding_str = ",".join(str(v) for v in embedding)
                embedding_value = f"'[{embedding_str}]'"
                print("✓")
            else:
                print("✗ (no embedding)")

            # Rate limiting: small delay between requests
            if i < total - 1:
                time.sleep(0.1)

        # Format arrays
        grape_varieties = "'{" + ",".join(f'"{g}"' for g in wine["grape_varieties"]) + "}'"
        food_pairings = "NULL"
        if wine.get("food_pairings"):
            food_pairings = "'{" + ",".join(f'"{f}"' for f in wine["food_pairings"]) + "}'"

        # Escape single quotes in text fields
        name = wine["name"].replace("'", "''")
        producer = wine["producer"].replace("'", "''")
        country = wine["country"].replace("'", "''")
        region = wine["region"].replace("'", "''")
        appellation = f"'{wine['appellation'].replace(chr(39), chr(39)+chr(39))}'" if wine.get("appellation") else "NULL"
        description = wine["description"].replace("'", "''")
        tasting_notes = f"'{wine['tasting_notes'].replace(chr(39), chr(39)+chr(39))}'" if wine.get("tasting_notes") else "NULL"
        image_url = f"'{wine['image_url']}'" if wine.get("image_url") else "NULL"
        vintage_year = wine.get("vintage_year") or "NULL"

        sql = f"""
            INSERT INTO wines (
                id, name, producer, vintage_year, country, region, appellation,
                grape_varieties, wine_type, sweetness, acidity, tannins, body,
                description, tasting_notes, food_pairings, price_rub, price_range,
                image_url, embedding
            ) VALUES (
                '{wine_id}',
                '{name}',
                '{producer}',
                {vintage_year},
                '{country}',
                '{region}',
                {appellation},
                {grape_varieties},
                '{wine["wine_type"]}',
                '{wine["sweetness"]}',
                {wine["acidity"]},
                {wine["tannins"]},
                {wine["body"]},
                '{description}',
                {tasting_notes},
                {food_pairings},
                {wine["price_rub"]},
                '{wine["price_range"]}',
                {image_url},
                {embedding_value}
            )
        """
        op.execute(sql)

    # Run ANALYZE for better query performance
    op.execute("ANALYZE wines")
    print(f"Done! Seeded {total} wines.")


def downgrade() -> None:
    # Remove all seeded wines
    op.execute("DELETE FROM wines")
