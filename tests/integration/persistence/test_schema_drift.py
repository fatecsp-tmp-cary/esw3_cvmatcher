"""The CI migration gate must agree with the complete persistence metadata."""

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.schema import CreateIndex

from src.persistence.job.job import Job


def test_migrated_database_has_no_unreviewed_schema_drift(db_engine):
    config = Config()
    config.set_main_option("script_location", "migrations")
    command.check(config)


def test_fts_index_matches_postgresql_parsed_expression_and_predicate(db_engine):
    """Compare in PostgreSQL rather than ignore an expression normalization gap."""
    index = next(index for index in Job.__table__.indexes if index.name == "ix_jobs_active_fts")
    with db_engine.begin() as connection:
        ddl = str(CreateIndex(index).compile(dialect=connection.dialect))
        connection.execute(text(ddl.replace("ix_jobs_active_fts", "ix_jobs_fts_schema_probe", 1)))
        query = text(
            "SELECT am.amname,i.indisunique,i.indisvalid,i.indisready,"
            "pg_get_expr(i.indexprs,i.indrelid),pg_get_expr(i.indpred,i.indrelid) "
            "FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid "
            "JOIN pg_am am ON am.oid=c.relam WHERE c.oid=CAST(:name AS regclass)"
        )
        actual = connection.execute(query, {"name": "ix_jobs_active_fts"}).one()
        expected = connection.execute(query, {"name": "ix_jobs_fts_schema_probe"}).one()
        assert tuple(actual) == tuple(expected)
        assert actual[:4] == ("gin", False, True, True)
        connection.execute(text("DROP INDEX ix_jobs_fts_schema_probe"))
