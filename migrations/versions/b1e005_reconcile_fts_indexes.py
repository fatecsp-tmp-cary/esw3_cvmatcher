"""Reconcile all FTS expressions with accepted main weights and field coverage.

Revision ID: b1e005
Revises: b1e004
"""

import sqlalchemy as sa
from alembic import op

revision = "b1e005"
down_revision = "b1e004"
branch_labels = None
depends_on = None

# Frozen SQL only: historical migrations are never imported or rewritten.

_JOB = (
    "(setweight(to_tsvector('pg_catalog.portuguese'::regconfig, coalesce(coalesc"
    "e(title, ''::text) || ' '::text || coalesce(CAST(skills AS TEXT), ''::text)"
    ", ''::text)), 'A') || setweight(to_tsvector('pg_catalog.portuguese'::regcon"
    "fig, coalesce(coalesce(company, ''::text) || ' '::text || coalesce(CAST(key"
    "words AS TEXT), ''::text), ''::text)), 'B')) || setweight(to_tsvector('pg_c"
    "atalog.portuguese'::regconfig, coalesce(coalesce(description, ''::text) || "
    "' '::text || coalesce(CAST(location AS TEXT), ''::text), ''::text)), 'D')"
)

_REQUIREMENT = (
    "setweight(to_tsvector('pg_catalog.portuguese'::regconfig, coalesce(text, ''::text)), 'B')"
)

_OLD_JOB = (
    "(setweight(to_tsvector('portuguese'::regconfig, coalesce(title, '') || ' ' "
    "|| coalesce(skills::text, '')), 'A') || setweight(to_tsvector('portuguese':"
    ":regconfig, coalesce(company, '') || ' ' || coalesce(keywords::text, '')), "
    "'B') || setweight(to_tsvector('portuguese'::regconfig, coalesce(description"
    ", '') || ' ' || coalesce(location::text, '')), 'D'))"
)

_OLD_REQUIREMENT = "to_tsvector('portuguese'::regconfig, text)"

_OLD_ACTIVE = (
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


def _replace(job_document: str, requirement_document: str, active_document: str) -> None:
    op.drop_index("ix_jobs_active_fts", table_name="jobs")
    op.drop_index("ix_jobs_search_portuguese", table_name="jobs")
    op.drop_index("ix_job_requirements_search_portuguese", table_name="job_requirements")
    op.create_index(
        "ix_jobs_search_portuguese",
        "jobs",
        [sa.text("(" + job_document + ")")],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_jobs_active_fts",
        "jobs",
        [sa.text("(" + active_document + ")")],
        postgresql_using="gin",
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "ix_job_requirements_search_portuguese",
        "job_requirements",
        [sa.text("(" + requirement_document + ")")],
        postgresql_using="gin",
    )


def upgrade() -> None:
    _replace(_JOB, _REQUIREMENT, _JOB)


def downgrade() -> None:
    _replace(_OLD_JOB, _OLD_REQUIREMENT, _OLD_ACTIVE)
