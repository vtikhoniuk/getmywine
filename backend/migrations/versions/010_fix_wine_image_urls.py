"""Fix wine image URLs: replace Wikimedia Special:FilePath redirects with direct URLs

Revision ID: 010
Revises: 009
Create Date: 2026-02-06

"""
import json
from pathlib import Path
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Load current seed data with corrected URLs
    seed_path = Path(__file__).resolve().parents[2] / "app" / "data" / "wines_seed.json"
    with open(seed_path) as f:
        data = json.load(f)

    for wine in data["wines"]:
        image_url = wine.get("image_url")
        if not image_url:
            continue
        name = wine["name"].replace("'", "''")
        image_url_escaped = image_url.replace("'", "''")
        op.execute(
            f"UPDATE wines SET image_url = '{image_url_escaped}' WHERE name = '{name}'"
        )


def downgrade() -> None:
    # No reliable way to restore old URLs; this is data-only
    pass
