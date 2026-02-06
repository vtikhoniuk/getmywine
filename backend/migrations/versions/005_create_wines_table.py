"""Create wines table with pgvector

Revision ID: 005
Revises: 004
Create Date: 2026-02-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create enum types
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE wine_type AS ENUM ('red', 'white', 'rose', 'sparkling');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE sweetness AS ENUM ('dry', 'semi_dry', 'semi_sweet', 'sweet');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE price_range AS ENUM ('budget', 'mid', 'premium');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create wines table
    op.create_table(
        "wines",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("producer", sa.String(255), nullable=False),
        sa.Column("vintage_year", sa.Integer(), nullable=True),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("region", sa.String(255), nullable=False),
        sa.Column("appellation", sa.String(255), nullable=True),
        sa.Column("grape_varieties", sa.ARRAY(sa.String(100)), nullable=False),
        sa.Column(
            "wine_type",
            postgresql.ENUM("red", "white", "rose", "sparkling", name="wine_type", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "sweetness",
            postgresql.ENUM("dry", "semi_dry", "semi_sweet", "sweet", name="sweetness", create_type=False),
            nullable=False,
        ),
        sa.Column("acidity", sa.Integer(), nullable=False),
        sa.Column("tannins", sa.Integer(), nullable=False),
        sa.Column("body", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tasting_notes", sa.Text(), nullable=True),
        sa.Column("food_pairings", sa.ARRAY(sa.String(100)), nullable=True),
        sa.Column("price_rub", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "price_range",
            postgresql.ENUM("budget", "mid", "premium", name="price_range", create_type=False),
            nullable=False,
        ),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "vintage_year IS NULL OR (vintage_year >= 1900 AND vintage_year <= 2030)",
            name="ck_wines_vintage_year",
        ),
        sa.CheckConstraint("acidity >= 1 AND acidity <= 5", name="ck_wines_acidity"),
        sa.CheckConstraint("tannins >= 1 AND tannins <= 5", name="ck_wines_tannins"),
        sa.CheckConstraint("body >= 1 AND body <= 5", name="ck_wines_body"),
        sa.CheckConstraint("price_rub > 0", name="ck_wines_price_rub"),
    )

    # Create indexes
    op.create_index("ix_wines_name", "wines", ["name"])
    op.create_index("ix_wines_wine_type", "wines", ["wine_type"])
    op.create_index("ix_wines_price_rub", "wines", ["price_rub"])
    op.create_index("ix_wines_country", "wines", ["country"])

    # Create HNSW index for vector similarity search
    op.execute("""
        CREATE INDEX ix_wines_embedding ON wines
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.drop_index("ix_wines_embedding", table_name="wines")
    op.drop_index("ix_wines_country", table_name="wines")
    op.drop_index("ix_wines_price_rub", table_name="wines")
    op.drop_index("ix_wines_wine_type", table_name="wines")
    op.drop_index("ix_wines_name", table_name="wines")
    op.drop_table("wines")

    op.execute("DROP TYPE IF EXISTS price_range")
    op.execute("DROP TYPE IF EXISTS sweetness")
    op.execute("DROP TYPE IF EXISTS wine_type")
