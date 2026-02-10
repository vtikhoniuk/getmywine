"""Nullify generic stock photo URLs (Unsplash) — keep only real bottle photos

Revision ID: 011
Revises: 010
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op: migration 012 replaces all wine data including image URLs
    pass


def downgrade() -> None:
    pass
