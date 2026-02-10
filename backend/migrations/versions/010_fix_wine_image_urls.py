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
    # No-op: migration 012 replaces all wine data including image URLs
    pass


def downgrade() -> None:
    pass
