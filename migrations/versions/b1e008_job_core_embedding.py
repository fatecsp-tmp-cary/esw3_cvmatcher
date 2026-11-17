"""Add the job-core embedding to job embedding provenance (ADR-027).

The canonical ``jobs`` table keeps exactly its accepted fields; the second,
internal job vector lives in the separate 1:1 ``job_embeddings`` structure.

Revision ID: b1e008
Revises: b1e007
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "b1e008"
down_revision = "b1e007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable: existing rows are re-embedded by the worker after the
    # JOB_TEXT_VERSION change; readiness requires both vectors meanwhile.
    op.add_column("job_embeddings", sa.Column("core_embedding", Vector(), nullable=True))


def downgrade() -> None:
    op.drop_column("job_embeddings", "core_embedding")
