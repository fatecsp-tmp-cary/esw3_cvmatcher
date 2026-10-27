"""create initial job persistence tables

Revision ID: 4d6249817e17
Revises: a627ed737076
Create Date: 2026-10-17 03:56:23.575884
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d6249817e17"
down_revision: str | Sequence[str] | None = "a627ed737076"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the initial job persistence tables."""

    # Create job sources.
    op.create_table(
        "job_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("polling_mode", sa.String(length=50), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
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
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("source_job_id", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.JSON(), nullable=True),
        sa.Column(
            "work_arrangement",
            sa.Enum("REMOTE", "HYBRID", "ON_SITE", name="workarrangement"),
            nullable=True,
        ),
        sa.Column(
            "seniority_level",
            sa.Enum(
                "INTERN",
                "JUNIOR",
                "MID",
                "SENIOR",
                "SPECIALIST",
                "COORDINATOR",
                name="senioritylevel",
            ),
            nullable=True,
        ),
        sa.Column("skills", sa.JSON(), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("salary", sa.JSON(), nullable=True),
        sa.Column("job_url", sa.Text(), nullable=True),
        sa.Column("publication_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "EXPIRED", name="jobstatus"),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["job_sources.id"],
            name=op.f("fk_jobs_source_id_job_sources"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
        sa.UniqueConstraint(
            "platform",
            "source_job_id",
            name=op.f("uq_jobs_platform"),
        ),
    )

    # Create indexes only after the jobs table exists.
    op.create_index("ix_jobs_publication_date", "jobs", ["publication_date"])
    op.create_index("ix_jobs_source_id", "jobs", ["source_id"])

    # Create source execution history.
    op.create_table(
        "source_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "snapshot_complete",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("jobs_found", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("jobs_created", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("jobs_updated", sa.Integer(), server_default=sa.text("0"), nullable=False),
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
    op.drop_index("ix_jobs_source_id", table_name="jobs")
    op.drop_index("ix_jobs_publication_date", table_name="jobs")
    op.drop_table("jobs")

    # Remove PostgreSQL enums created for normalization fields.
    sa.Enum(name="jobstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="senioritylevel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="workarrangement").drop(op.get_bind(), checkfirst=True)

    # Remove job sources.
    op.drop_table("job_sources")
