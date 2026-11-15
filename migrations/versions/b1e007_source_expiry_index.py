"""Index due reliable source timestamps on nonterminal jobs.

Revision ID: b1e007
Revises: b1e006
"""

import sqlalchemy as sa
from alembic import op

revision = "b1e007"
down_revision = "b1e006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_jobs_due_source_expiry",
        "jobs",
        ["source_expires_at"],
        postgresql_where=sa.text(
            "source_expires_at IS NOT NULL AND status IN ('DISCOVERED', 'ACTIVE', 'STALE')"
        ),
    )


def downgrade():
    op.drop_index("ix_jobs_due_source_expiry", table_name="jobs")
