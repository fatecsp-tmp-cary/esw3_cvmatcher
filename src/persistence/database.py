import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def database_url() -> str:
    url = os.environ["DATABASE_URL"]
    # A bare postgresql:// URL selects psycopg2 in SQLAlchemy; the project uses psycopg 3.
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def create_db_engine(url: str | None = None) -> Engine:
    return create_engine(url or database_url())


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine)
