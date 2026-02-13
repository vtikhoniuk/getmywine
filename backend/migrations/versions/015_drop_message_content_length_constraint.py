"""Drop messages.content CHECK constraint (char_length <= 2000)

Revision ID: 015
Revises: 014
Create Date: 2026-02-13

PostgreSQL Text type has no practical length limit. The CHECK constraint
was an artificial cap that caused truncation of LLM responses before storage.
Removing it allows full assistant responses to be preserved in conversation
history. See spec 021-message-length-limit.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_messages_content_length", "messages", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "ck_messages_content_length",
        "messages",
        "char_length(content) <= 2000",
    )
