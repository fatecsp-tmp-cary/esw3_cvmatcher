"""Add Portuguese GIN indexes for jobs and job requirements.

Revision ID: 8c317a55d4b1
Revises: 7ad019c623bf
Create Date: 2026-10-27 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c317a55d4b1"
down_revision: str | Sequence[str] | None = "7ad019c623bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Index searchable job fields and normalized requirement text."""
    op.create_index(
        "ix_jobs_search_portuguese",
        "jobs",
        [
            sa.text(
                "to_tsvector('portuguese'::regconfig, "
                "concat_ws(' ', title, company, description, keywords::text, "
                "skills::text, location::text))"
            )
        ],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_job_requirements_search_portuguese",
        "job_requirements",
        [sa.text("to_tsvector('portuguese'::regconfig, text)")],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Remove the full-text indexes."""
    op.drop_index("ix_job_requirements_search_portuguese", table_name="job_requirements")
    op.drop_index("ix_jobs_search_portuguese", table_name="jobs")
