from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session


@pytest.fixture(scope="module")
def example_table(db_engine: Engine) -> Iterator[None]:
    """A throwaway table so these examples don't depend on any real schema."""
    with db_engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE fixture_example (id integer PRIMARY KEY, label text NOT NULL)")
        )
    yield
    with db_engine.begin() as connection:
        connection.execute(text("DROP TABLE fixture_example"))


def _insert(session: Session, row_id: int, label: str) -> None:
    session.execute(
        text("INSERT INTO fixture_example (id, label) VALUES (:id, :label)"),
        {"id": row_id, "label": label},
    )


def _count(session: Session) -> int:
    return session.scalar(text("SELECT count(*) FROM fixture_example"))


def test_migrations_are_applied(db_session: Session):
    version = db_session.scalar(text("SELECT version_num FROM alembic_version"))

    assert version is not None


@pytest.mark.usefixtures("example_table")
def test_session_writes_and_reads(db_session: Session):
    _insert(db_session, 1, "first")

    label = db_session.scalar(text("SELECT label FROM fixture_example WHERE id = 1"))

    assert label == "first"


@pytest.mark.usefixtures("example_table")
def test_commit_inside_a_test_is_still_discarded(db_session: Session):
    _insert(db_session, 1, "committed")
    db_session.commit()

    assert _count(db_session) == 1


@pytest.mark.usefixtures("example_table")
def test_data_from_previous_tests_is_not_visible(db_session: Session):
    assert _count(db_session) == 0


@pytest.mark.usefixtures("example_table")
def test_same_primary_key_can_be_reused_across_tests(db_session: Session):
    # Would raise a unique violation if an earlier test's row 1 had leaked.
    _insert(db_session, 1, "again")

    assert _count(db_session) == 1
