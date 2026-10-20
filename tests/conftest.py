import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from src.persistence.database import create_db_engine, database_url

PROJECT_ROOT = Path(__file__).parent.parent
TESTS_ROOT = Path(__file__).parent

# First directory under tests/ -> marker applied to every test inside it.
DIRECTORY_MARKERS = {
    "unit": "unit",
    "integration": "integration",
    "api": "api",
    "e2e": "e2e",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        relative = item.path.relative_to(TESTS_ROOT)
        marker = DIRECTORY_MARKERS.get(relative.parts[0])
        if marker is not None:
            item.add_marker(marker)


def _ensure_database_exists(url: URL) -> None:
    """Create the test database on first use so local setup needs no extra step."""
    maintenance = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with maintenance.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
            )
            if not exists:
                quoted = maintenance.dialect.identifier_preparer.quote(url.database)
                connection.execute(text(f"CREATE DATABASE {quoted}"))
    finally:
        maintenance.dispose()


@pytest.fixture(scope="session")
def test_database_url() -> Iterator[str]:
    """Connection URL of the test database, taken from TEST_DATABASE_URL.

    DATABASE_URL is pointed at the same database for the whole session, so Alembic and
    any application code under test can never reach the development database.
    """
    raw = os.environ.get("TEST_DATABASE_URL")
    if not raw:
        pytest.skip("TEST_DATABASE_URL is not set; see 'Database-backed tests' in the README")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("DATABASE_URL", raw)
        url = database_url()
        name = make_url(url).database
        if not name or not name.endswith("_test"):
            pytest.fail(
                f"Refusing to run against database {name!r}: the name must end in '_test' "
                "so tests never touch development data",
                pytrace=False,
            )
        yield url


@pytest.fixture(scope="session")
def db_engine(test_database_url: str) -> Iterator[Engine]:
    """Engine for the test database with all migrations applied.

    Applies `alembic upgrade head` once per session and `downgrade base` at the end,
    so every run starts from the schema the migrations describe.
    """
    try:
        _ensure_database_exists(make_url(test_database_url))
    except OperationalError as error:
        pytest.fail(
            f"Could not connect to PostgreSQL; is it running? (`docker compose up -d`)\n{error}",
            pytrace=False,
        )

    # No ini file: Alembic's logging setup would otherwise replace pytest's log handlers.
    config = Config()
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))

    command.upgrade(config, "head")
    engine = create_db_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")


@pytest.fixture
def db_connection(db_engine: Engine) -> Iterator[Connection]:
    """A connection inside an outer transaction that is rolled back after the test."""
    with db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.fixture
def db_session(db_connection: Connection) -> Iterator[Session]:
    """An isolated ORM session: whatever a test writes, even with commit(), is discarded.

    The session runs in a SAVEPOINT of the outer transaction, so `commit()` and
    `rollback()` inside a test behave normally but never reach the database for real.
    """
    session = Session(bind=db_connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
