"""create initial job persistence tables

Revision ID: 4d6249817e17
Revises: a627ed737076
Create Date: 2026-10-17 03:56:23.575884
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR

# revision identifiers, used by Alembic.
revision: str = "4d6249817e17"
down_revision: str | Sequence[str] | None = "a627ed737076"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial job persistence tables."""

    # Enable pgvector before creating the embedding column.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create job sources.
    op.create_table(
        "job_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("polling_mode", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("polling_interval", sa.Integer(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_sources")),
        sa.UniqueConstraint("name", name=op.f("uq_job_sources_name")),
    )

    # Create normalized jobs.
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_job_id", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("mode", sa.String(length=50), nullable=True),
        sa.Column("salary", sa.String(length=100), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("employment_type", sa.String(length=100), nullable=True),
        sa.Column("requirements", sa.JSON(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DISCOVERED",
                "ACTIVE",
                "STALE",
                "EXPIRED",
                name="jobstatus",
            ),
            nullable=False,
        ),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("embedding", VECTOR(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint(
            "source",
            "source_job_id",
            name=op.f("uq_jobs_source"),
        ),
    )

    # Create indexes only after the jobs table exists.
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_published_at", "jobs", ["published_at"])

    # Create source execution history.
    op.create_table(
        "source_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("snapshot_complete", sa.Boolean(), nullable=False),
        sa.Column("jobs_found", sa.Integer(), nullable=False),
        sa.Column("jobs_created", sa.Integer(), nullable=False),
        sa.Column("jobs_updated", sa.Integer(), nullable=False),
        sa.Column("lifecycle_changes", sa.Integer(), nullable=False),
        sa.Column("errors", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["job_sources.id"],
            name=op.f("fk_source_runs_source_id_job_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_runs")),
    )

    op.create_index(
        "ix_source_runs_source_id",
        "source_runs",
        ["source_id"],
    )

    # Remove the temporary migration-tooling test table.
    op.drop_table("tooling_check")


def downgrade() -> None:
    """Restore the schema to the previous migration."""

    # Restore the temporary tooling table.
    op.create_table(
        "tooling_check",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tooling_check")),
    )

    # Remove source execution history.
    op.drop_index("ix_source_runs_source_id", table_name="source_runs")
    op.drop_table("source_runs")

    # Remove jobs and their indexes.
    op.drop_index("ix_jobs_published_at", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")

    # Remove the PostgreSQL enum created for job status.
    sa.Enum(name="jobstatus").drop(op.get_bind(), checkfirst=True)

    # Remove job sources.
    op.drop_table("job_sources")

    # Keep the vector extension installed because other objects may use it.
