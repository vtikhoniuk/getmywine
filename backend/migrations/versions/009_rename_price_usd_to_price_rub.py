"""Rename price_usd to price_rub and convert values (USD * 80)

Revision ID: 009
Revises: 008
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008_telegram"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename column
    op.alter_column("wines", "price_usd", new_column_name="price_rub")

    # Convert USD to RUB (multiply by 80)
    op.execute("UPDATE wines SET price_rub = price_rub * 80")

    # Rename constraint and index
    op.drop_constraint("ck_wines_price_usd", "wines", type_="check")
    op.create_check_constraint("ck_wines_price_rub", "wines", "price_rub > 0")

    op.drop_index("ix_wines_price_usd", table_name="wines")
    op.create_index("ix_wines_price_rub", "wines", ["price_rub"])


def downgrade() -> None:
    # Rename back
    op.alter_column("wines", "price_rub", new_column_name="price_usd")

    # Convert RUB back to USD (divide by 80)
    op.execute("UPDATE wines SET price_usd = price_usd / 80")

    # Rename constraint and index back
    op.drop_constraint("ck_wines_price_rub", "wines", type_="check")
    op.create_check_constraint("ck_wines_price_usd", "wines", "price_usd > 0")

    op.drop_index("ix_wines_price_rub", table_name="wines")
    op.create_index("ix_wines_price_usd", "wines", ["price_usd"])
