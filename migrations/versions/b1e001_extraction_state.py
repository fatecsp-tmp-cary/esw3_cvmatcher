"""Separate extraction readiness and job span evidence.

Revision ID: b1e001
Revises: 91d0a7f3bc22
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b1e001"
down_revision = "91d0a7f3bc22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_extractions",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(255), nullable=False),
        sa.Column("config_version", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("claim_token", sa.String(36)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(32)),
        sa.Column("evidence", postgresql.JSONB()),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','SUCCEEDED','FAILED')", name="ck_job_extractions_status"
        ),
        sa.CheckConstraint("attempts >= 0 AND attempts <= 3", name="ck_job_extractions_attempts"),
        sa.CheckConstraint(
            "(status = 'RUNNING') = (claim_token IS NOT NULL)", name="ck_job_extractions_claim"
        ),
        sa.CheckConstraint(
            "(status = 'RUNNING') = (lease_expires_at IS NOT NULL)", name="ck_job_extractions_lease"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        "ix_job_extractions_pending", "job_extractions", ["status", "next_attempt_at", "job_id"]
    )


def downgrade() -> None:
    op.drop_table("job_extractions")
