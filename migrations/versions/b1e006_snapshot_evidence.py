"""Store bounded best-effort source snapshot evidence outside canonical Job.

Revision ID: b1e006
Revises: b1e005
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b1e006"
down_revision = "b1e005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("source_runs", sa.Column("snapshot_evidence", postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column("source_runs", "snapshot_evidence")
