"""Separate job embedding provenance and bounded retry metadata.

Revision ID: b1e002
Revises: b1e001
"""

import sqlalchemy as sa
from alembic import op

revision = "b1e002"
down_revision = "b1e001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_embeddings",
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(255), nullable=False),
        sa.Column("model_version", sa.String(512), nullable=False),
        sa.Column("extraction_version", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("claim_token", sa.String(36)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(32)),
        sa.CheckConstraint(
            "status IN ('PENDING','RUNNING','SUCCEEDED','FAILED')",
            name=op.f("ck_job_embeddings_status"),
        ),
        sa.CheckConstraint(
            "attempts >= 0 AND attempts <= 3", name=op.f("ck_job_embeddings_attempts")
        ),
        sa.CheckConstraint(
            "(status = 'RUNNING') = (claim_token IS NOT NULL)", name=op.f("ck_job_embeddings_claim")
        ),
        sa.CheckConstraint(
            "(status = 'RUNNING') = (lease_expires_at IS NOT NULL)",
            name=op.f("ck_job_embeddings_lease"),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index(
        "ix_job_embeddings_pending", "job_embeddings", ["status", "next_attempt_at", "job_id"]
    )


def downgrade() -> None:
    op.drop_table("job_embeddings")
