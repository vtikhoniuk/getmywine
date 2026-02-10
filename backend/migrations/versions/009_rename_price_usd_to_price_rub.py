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
    # No-op: migration 005 already creates column as price_rub
    pass


def downgrade() -> None:
    pass
