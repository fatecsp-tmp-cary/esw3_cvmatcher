"""Add lifecycle and execution evidence to source runs.

Revision ID: 6f4ad83a91c0
Revises: 4d6249817e17
Create Date: 2026-10-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f4ad83a91c0"
down_revision: str | Sequence[str] | None = "4d6249817e17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record polling mode, duration, and job lifecycle counts per source run."""
    op.add_column("source_runs", sa.Column("polling_mode", sa.String(length=50), nullable=True))
    op.execute(
        """
        UPDATE source_runs AS runs
        SET polling_mode = sources.polling_mode
        FROM job_sources AS sources
        WHERE runs.source_id = sources.id
        """
    )
    op.alter_column(
        "source_runs",
        "polling_mode",
        existing_type=sa.String(length=50),
        nullable=False,
    )
    op.add_column("source_runs", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column(
        "source_runs",
        sa.Column(
            "jobs_unchanged",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "source_runs",
        sa.Column("jobs_absent", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "source_runs",
        sa.Column(
            "jobs_marked_stale",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "source_runs",
        sa.Column("jobs_expired", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.add_column(
        "source_runs",
        sa.Column(
            "jobs_reactivated",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Remove the additional source-run evidence."""
    op.drop_column("source_runs", "jobs_reactivated")
    op.drop_column("source_runs", "jobs_expired")
    op.drop_column("source_runs", "jobs_marked_stale")
    op.drop_column("source_runs", "jobs_absent")
    op.drop_column("source_runs", "jobs_unchanged")
    op.drop_column("source_runs", "duration_ms")
    op.drop_column("source_runs", "polling_mode")
