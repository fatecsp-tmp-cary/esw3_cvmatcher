from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text


def test_canonical_migrations_round_trip_existing_data(db_engine):
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parents[3] / "migrations"))
    source_id = None
    try:
        command.downgrade(config, "4d6249817e17")
        with db_engine.begin() as connection:
            source_id = connection.scalar(
                text(
                    "INSERT INTO job_sources (name, type, polling_mode) "
                    "VALUES ('migration-regression', 'api', 'INCREMENTAL') RETURNING id"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO jobs (source_id, platform, source_job_id, title) "
                    "VALUES (:id, 'migration', 'old', 'Python')"
                ),
                {"id": source_id},
            )
        command.upgrade(config, "head")
        with db_engine.begin() as connection:
            connection.execute(
                text("UPDATE jobs SET status = 'DISCOVERED' WHERE platform = 'migration'")
            )
            connection.execute(
                text(
                    "INSERT INTO jobs (source_id, platform, source_job_id, title, status) "
                    "VALUES (:id, 'migration', 'stale', 'Django', 'STALE')"
                ),
                {"id": source_id},
            )
        command.downgrade(config, "4d6249817e17")
        with db_engine.connect() as connection:
            assert connection.execute(
                text("SELECT status::text FROM jobs WHERE platform = 'migration'")
            ).scalars().all() == ["ACTIVE", "ACTIVE"]
            assert connection.execute(
                text(
                    "SELECT enumlabel FROM pg_enum JOIN pg_type ON enumtypid = pg_type.oid "
                    "WHERE typname = 'jobstatus' ORDER BY enumsortorder"
                )
            ).scalars().all() == ["ACTIVE", "EXPIRED"]
    finally:
        command.upgrade(config, "head")
        if source_id is not None:
            with db_engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM jobs WHERE source_id = :id"), {"id": source_id}
                )
                connection.execute(
                    text("DELETE FROM job_sources WHERE id = :id"), {"id": source_id}
                )
