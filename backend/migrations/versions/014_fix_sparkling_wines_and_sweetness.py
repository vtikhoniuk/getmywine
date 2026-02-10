"""Fix sparkling wines wine_type and Asti sweetness

Revision ID: 014
Revises: 013
Create Date: 2026-02-10

6 sparkling wines were incorrectly labeled as wine_type='white'.
Bruni Asti was incorrectly labeled as sweetness='dry' (should be 'sweet').
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Wines that should be sparkling (matched by name substring)
SPARKLING_WINES = [
    "Bruni Prosecco Brut",
    "Prosecco Superiore Valdobbiadene Quartese Brut",
    "Bruni Asti",
    "Le Black Creation Brut",
    "Балаклава Брют Резерв",
    "Santa Carolina Brut",
]


def upgrade() -> None:
    conn = op.get_bind()

    # Fix wine_type for sparkling wines
    for name in SPARKLING_WINES:
        conn.execute(
            sa.text(
                "UPDATE wines SET wine_type = 'sparkling' "
                "WHERE name LIKE :pattern AND wine_type = 'white'"
            ),
            {"pattern": f"%{name}%"},
        )

    # Fix sweetness for Bruni Asti
    conn.execute(
        sa.text(
            "UPDATE wines SET sweetness = 'sweet' "
            "WHERE name LIKE '%Bruni Asti%' AND sweetness = 'dry'"
        ),
    )

    print(f"Fixed wine_type to 'sparkling' for {len(SPARKLING_WINES)} wines.")
    print("Fixed sweetness to 'sweet' for Bruni Asti.")


def downgrade() -> None:
    conn = op.get_bind()

    for name in SPARKLING_WINES:
        conn.execute(
            sa.text(
                "UPDATE wines SET wine_type = 'white' "
                "WHERE name LIKE :pattern AND wine_type = 'sparkling'"
            ),
            {"pattern": f"%{name}%"},
        )

    conn.execute(
        sa.text(
            "UPDATE wines SET sweetness = 'dry' "
            "WHERE name LIKE '%Bruni Asti%' AND sweetness = 'sweet'"
        ),
    )
