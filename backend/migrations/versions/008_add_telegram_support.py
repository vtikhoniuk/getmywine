"""Add Telegram bot support.

Revision ID: 008_telegram
Revises: 007_sessions
Create Date: 2026-02-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "008_telegram"
down_revision: Union[str, None] = "007_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create telegram_users table
    op.create_table(
        "telegram_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column(
            "language_code", sa.String(10), nullable=False, server_default="ru"
        ),
        sa.Column(
            "is_age_verified", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_telegram_users_telegram_id",
        "telegram_users",
        ["telegram_id"],
        unique=True,
    )
    op.create_index(
        "ix_telegram_users_user_id",
        "telegram_users",
        ["user_id"],
    )

    # Extend conversations table
    # Step 1: Add channel column with default
    op.add_column(
        "conversations",
        sa.Column(
            "channel", sa.String(20), nullable=False, server_default="web"
        ),
    )

    # Step 2: Add telegram_user_id column (nullable)
    op.add_column(
        "conversations",
        sa.Column("telegram_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Step 3: Create foreign key constraint
    op.create_foreign_key(
        "fk_conversations_telegram_user_id",
        "conversations",
        "telegram_users",
        ["telegram_user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Step 4: Create index for telegram queries
    op.create_index(
        "ix_conversations_telegram_user_id",
        "conversations",
        ["telegram_user_id"],
    )

    # Step 5: Make user_id nullable (for Telegram-only conversations)
    op.alter_column(
        "conversations",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # Revert user_id to non-nullable
    # Note: This will fail if there are rows with null user_id
    op.alter_column(
        "conversations",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # Drop telegram support from conversations
    op.drop_index("ix_conversations_telegram_user_id", table_name="conversations")
    op.drop_constraint(
        "fk_conversations_telegram_user_id", "conversations", type_="foreignkey"
    )
    op.drop_column("conversations", "telegram_user_id")
    op.drop_column("conversations", "channel")

    # Drop telegram_users table
    op.drop_index("ix_telegram_users_user_id", table_name="telegram_users")
    op.drop_index("ix_telegram_users_telegram_id", table_name="telegram_users")
    op.drop_table("telegram_users")
