"""Anonymous, PostgreSQL-coordinated rolling admission limit across API workers."""

from threading import Lock

from sqlalchemy import Engine, text

from src.persistence.database import create_db_engine


class GlobalRateLimiter:
    def __init__(self, engine: Engine | None = None, *, limit: int = 60, seconds: int = 60):
        if limit < 1 or seconds < 1:
            raise ValueError("positive rate limit and window are required")
        self._engine = engine
        self._lock = Lock()
        self.limit = limit
        self.seconds = seconds

    def allow(self) -> bool:
        with self._lock:
            if self._engine is None:
                self._engine = create_db_engine()
            engine = self._engine
        with engine.begin() as connection:
            # Two-int advisory keys are separate from ingestion's bigint keys.
            connection.execute(text("SELECT pg_advisory_xact_lock(1129729364, 60)"))
            now = connection.scalar(text("SELECT clock_timestamp()"))
            connection.execute(
                text(
                    "DELETE FROM api_admissions WHERE admitted_at <= "
                    ":now - :seconds * interval '1 second'"
                ),
                {"now": now, "seconds": self.seconds},
            )
            count = connection.scalar(text("SELECT count(*) FROM api_admissions"))
            if count >= self.limit:
                return False
            connection.execute(
                text("INSERT INTO api_admissions (admitted_at) VALUES (:now)"), {"now": now}
            )
            return True
