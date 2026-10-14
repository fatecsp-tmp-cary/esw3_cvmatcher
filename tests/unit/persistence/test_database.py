import pytest

from src.persistence.database import database_url


@pytest.mark.parametrize(
    "raw",
    ["postgresql://u:p@localhost:5432/db", "postgres://u:p@localhost:5432/db"],
)
def test_database_url_selects_psycopg_driver(monkeypatch, raw):
    monkeypatch.setenv("DATABASE_URL", raw)

    assert database_url() == "postgresql+psycopg://u:p@localhost:5432/db"


def test_database_url_keeps_explicit_driver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")

    assert database_url() == "postgresql+psycopg://u:p@localhost:5432/db"


def test_database_url_requires_environment_variable(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(KeyError):
        database_url()
