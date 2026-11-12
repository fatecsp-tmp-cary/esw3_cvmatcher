from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from src.persistence import api_admission, embedding, extraction  # noqa: F401
from src.persistence.base import Base
from src.persistence.database import database_url
from src.persistence.job import job, job_source, skill, source_run  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # PostgreSQL expands implicit varchar/regconfig casts in this expression.
    # Alembic's string comparison reports a false replacement. Its exact parsed
    # expression, predicate, method and validity are checked against a generated
    # probe index by the required PostgreSQL schema-drift regression instead.
    return not (type_ == "index" and name == "ix_jobs_active_fts")


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
