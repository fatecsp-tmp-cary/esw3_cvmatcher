"""Index the immutable weighted Portuguese ACTIVE-job search expression.

Revision ID: b1e003
Revises: b1e002
"""

from alembic import op

revision = "b1e003"
down_revision = "b1e002"
branch_labels = None
depends_on = None

# Frozen migration expression: future ranking changes must use a new migration.
_DOCUMENT = (
    "((((setweight(to_tsvector('pg_catalog.portuguese'::regconfig, coalesce(titl"
    "e, ''::text)), 'A') || setweight(jsonb_to_tsvector('pg_catalog.portuguese':"
    ":regconfig, coalesce(CAST(skills AS JSONB), '[]'::jsonb), '[\"string\"]'::jso"
    "nb), 'B')) || setweight(jsonb_to_tsvector('pg_catalog.portuguese'::regconfi"
    "g, coalesce(CAST('[]'::jsonb AS JSONB), '[]'::jsonb), '[\"string\"]'::jsonb),"
    " 'B')) || setweight(to_tsvector('pg_catalog.portuguese'::regconfig, coalesc"
    "e(company, ''::text)), 'C')) || setweight(to_tsvector('pg_catalog.portugues"
    "e'::regconfig, coalesce(description, ''::text)), 'D')) || setweight(jsonb_t"
    "o_tsvector('pg_catalog.portuguese'::regconfig, coalesce(CAST(location AS JS"
    "ONB), '[]'::jsonb), '[\"string\"]'::jsonb), 'D')"
)


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_jobs_active_fts ON jobs USING gin (("
        + _DOCUMENT
        + ")) WHERE status = 'ACTIVE'"
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_active_fts", table_name="jobs")
