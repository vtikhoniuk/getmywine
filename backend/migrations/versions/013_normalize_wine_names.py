"""Normalize wine names: remove category prefixes, producer, and year

Revision ID: 013
Revises: 012
Create Date: 2026-02-10

Applies normalize_wine_name() to all wines in the database.
Removes category prefix (Вино/Игристое вино/Шампанское), trailing
", {vintage_year}" and ", {producer}" from the name field.

This is an irreversible data migration (downgrade is a no-op).
"""

from typing import Sequence, Union

from alembic import op

from app.utils.wine_normalization import normalize_wine_name

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    rows = conn.execute(
        conn.engine.text(
            "SELECT id, name, producer, vintage_year FROM wines"
        )
    ).fetchall()

    updated = 0
    for row in rows:
        wine_id, old_name, producer, vintage_year = row
        new_name = normalize_wine_name(old_name, producer, vintage_year)

        if new_name != old_name:
            conn.execute(
                conn.engine.text(
                    "UPDATE wines SET name = :name WHERE id = :id"
                ),
                {"name": new_name, "id": wine_id},
            )
            updated += 1

    print(f"Normalized {updated} wine names out of {len(rows)} total.")


def downgrade() -> None:
    # Irreversible data migration — names can be restored from old seed
    pass
