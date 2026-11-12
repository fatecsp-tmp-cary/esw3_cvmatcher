"""Add global, anonymous API admission timestamps.

Revision ID: 91d0a7f3bc22
Revises: 6f4ad83a91c0
"""

from alembic import op

revision = "91d0a7f3bc22"
down_revision = "6f4ad83a91c0"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE TABLE api_admissions (admitted_at timestamptz NOT NULL)")


def downgrade():
    op.drop_table("api_admissions")
