"""create tooling_check table

Throwaway table that only exists to validate the migration tooling; the first real
schema migration is expected to drop it.

Revision ID: a627ed737076
Revises:
Create Date: 2026-10-11 18:57:27.192781

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a627ed737076"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tooling_check",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("note", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("tooling_check")
