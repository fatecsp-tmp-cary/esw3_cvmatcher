"""The CI migration gate must agree with the complete persistence metadata."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.schema import CreateIndex

from src.persistence.job.job import Job
from src.persistence.job.skill import JobRequirement


def test_migrated_database_has_no_unreviewed_schema_drift(db_engine):
    config = Config()
    config.set_main_option("script_location", "migrations")
    command.check(config)


@pytest.mark.parametrize(
    ("model", "index_name"),
    [
        (Job, "ix_jobs_active_fts"),
        (Job, "ix_jobs_search_portuguese"),
        (JobRequirement, "ix_job_requirements_search_portuguese"),
    ],
)
def test_fts_index_matches_postgresql_parsed_expression_and_predicate(db_engine, model, index_name):
    """Compare in PostgreSQL rather than ignore an expression normalization gap."""
    index = next(index for index in model.__table__.indexes if index.name == index_name)
    probe = index_name + "_probe"
    with db_engine.begin() as connection:
        ddl = str(CreateIndex(index).compile(dialect=connection.dialect))
        connection.execute(text(ddl.replace(index_name, probe, 1)))
        query = text(
            "SELECT am.amname,i.indisunique,i.indisvalid,i.indisready,"
            "pg_get_expr(i.indexprs,i.indrelid),pg_get_expr(i.indpred,i.indrelid) "
            "FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid "
            "JOIN pg_am am ON am.oid=c.relam WHERE c.oid=CAST(:name AS regclass)"
        )
        actual = connection.execute(query, {"name": index_name}).one()
        expected = connection.execute(query, {"name": probe}).one()
        assert tuple(actual) == tuple(expected)
        assert actual[:4] == ("gin", False, True, True)
        # Names above are fixed developer constants, never submitted SQL data.
        connection.execute(text(f"DROP INDEX {probe}"))
