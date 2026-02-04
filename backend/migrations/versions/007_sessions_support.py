"""Add sessions support to conversations.

Revision ID: 007_sessions
Revises: 006
Create Date: 2026-02-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_sessions"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Remove unique constraint on user_id to allow multiple sessions
    op.drop_constraint(
        "conversations_user_id_key",
        "conversations",
        type_="unique",
    )

    # Step 2: Add title column for session naming
    op.add_column(
        "conversations",
        sa.Column("title", sa.String(30), nullable=True),
    )

    # Step 3: Add closed_at column for session lifecycle
    op.add_column(
        "conversations",
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # Step 4: Create composite index for fast session list queries
    op.create_index(
        "idx_conversations_user_sessions",
        "conversations",
        ["user_id", sa.text("created_at DESC")],
    )

    # Step 5: Backfill titles for existing conversations with formatted date
    op.execute("""
        UPDATE conversations
        SET title = TO_CHAR(created_at, 'DD Mon')
        WHERE title IS NULL
    """)


def downgrade() -> None:
    # Drop the new index
    op.drop_index("idx_conversations_user_sessions", "conversations")

    # Drop new columns
    op.drop_column("conversations", "closed_at")
    op.drop_column("conversations", "title")

    # Note: Cannot restore unique constraint if multiple sessions exist per user
    # Manual data cleanup would be required before downgrading
