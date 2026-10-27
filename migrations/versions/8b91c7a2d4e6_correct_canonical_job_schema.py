"""correct canonical job schema

Revision ID: 8b91c7a2d4e6
Revises: 4d6249817e17
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "8b91c7a2d4e6"
down_revision: str | Sequence[str] | None = "4d6249817e17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Bring the initial persistence schema in line with the canonical Job."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # PostgreSQL enum additions need to be committed before setting the new
    # default that uses DISCOVERED.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'DISCOVERED'")
        op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'STALE'")

    op.add_column("jobs", sa.Column("source_expires_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("currency", sa.String(length=10)))
    op.add_column("jobs", sa.Column("last_verified_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("raw", sa.JSON()))
    op.add_column("jobs", sa.Column("embedding", Vector()))
    op.add_column("jobs", sa.Column("content_hash", sa.String(length=255)))
    op.alter_column(
        "jobs",
        "status",
        existing_type=sa.Enum("ACTIVE", "EXPIRED", name="jobstatus"),
        server_default="DISCOVERED",
    )
    op.drop_constraint("uq_jobs_platform", "jobs", type_="unique")
    op.create_unique_constraint(
        "uq_jobs_platform_source_job_id", "jobs", ["platform", "source_job_id"]
    )


def downgrade() -> None:
    """Remove added columns and restore the original unique constraint/default."""
    op.drop_constraint("uq_jobs_platform_source_job_id", "jobs", type_="unique")
    op.create_unique_constraint("uq_jobs_platform", "jobs", ["platform", "source_job_id"])
    op.alter_column(
        "jobs",
        "status",
        existing_type=sa.Enum("ACTIVE", "EXPIRED", "DISCOVERED", "STALE", name="jobstatus"),
        server_default="ACTIVE",
    )
    op.drop_column("jobs", "content_hash")
    op.drop_column("jobs", "embedding")
    op.drop_column("jobs", "raw")
    op.drop_column("jobs", "last_verified_at")
    op.drop_column("jobs", "currency")
    op.drop_column("jobs", "source_expires_at")
