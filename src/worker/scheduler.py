"""Source scheduling with session locks independent of ingestion transactions."""

import json
import logging
import re
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta, tzinfo
from typing import Protocol

from sqlalchemy import Engine, func, or_, select
from sqlalchemy.orm import Session

from src.ingestion.apibr import ingest_apibr
from src.persistence.job.job_source import JobSource

logger = logging.getLogger(__name__)
_LOCK_NAMESPACE = 1129729363


class PollResult(Protocol):
    @property
    def status(self) -> str: ...


SourcePoller = Callable[[Session, int], PollResult]


@dataclass(frozen=True, slots=True)
class PollOutcome:
    source_id: int
    status: str


def interval_seconds(configured: int | None, default: int = 3600) -> int:
    if isinstance(default, bool) or not isinstance(default, int) or default <= 0:
        raise ValueError("default polling interval must be a positive integer")
    return configured if type(configured) is int and configured > 0 else default


def parse_daily_time(value: str) -> time:
    """Parse a 24-hour ``HH:MM`` local polling time."""
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", value.strip())
    if match is None:
        raise ValueError("daily polling time must use the 24-hour HH:MM format")
    return time(int(match[1]), int(match[2]))


def next_daily_run(after: datetime, at: time, zone: tzinfo) -> datetime:
    """Return the first occurrence of local time ``at`` strictly after ``after``."""
    local = after.astimezone(zone)
    candidate = local.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate.astimezone(UTC)


@contextmanager
def source_lock(engine: Engine, source_id: int) -> Iterator[bool]:
    """Never return a connection with a held session lock to the pool.

    The lock connection must be separate from the ingestion Session: ingestion
    commits independently, and transaction-scoped locks would release too early.
    """
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        acquired = False
        try:
            try:
                acquired = bool(
                    connection.scalar(select(func.pg_try_advisory_lock(_LOCK_NAMESPACE, source_id)))
                )
            except Exception:
                connection.invalidate()
                raise
            yield acquired
        finally:
            if acquired:
                try:
                    released = connection.scalar(
                        select(func.pg_advisory_unlock(_LOCK_NAMESPACE, source_id))
                    )
                    if not released:
                        connection.invalidate()
                except Exception:
                    # Discard the physical connection on uncertain unlock. Closing
                    # the PostgreSQL session releases its session-level locks.
                    connection.invalidate()
                    raise


class SourceScheduler:
    def __init__(
        self,
        engine: Engine,
        sessions: Callable[[], Session],
        *,
        pollers: Mapping[str, SourcePoller] | None = None,
        default_interval_seconds: int = 3600,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        daily_at: time | None = None,
        timezone: tzinfo = UTC,
        startup_min_gap_seconds: int = 600,
    ) -> None:
        if type(startup_min_gap_seconds) is not int or startup_min_gap_seconds < 0:
            raise ValueError("startup polling gap must be a non-negative integer")
        self.engine = engine
        self.sessions = sessions
        self.pollers = dict(pollers) if pollers is not None else {"apibr": ingest_apibr}
        self.default_interval_seconds = interval_seconds(None, default_interval_seconds)
        self.clock = clock
        self.daily_at = daily_at
        self.timezone = timezone
        self.startup_min_gap = timedelta(seconds=startup_min_gap_seconds)

    def _next_run(self, after: datetime, interval: int) -> datetime:
        """A configured daily time replaces interval polling for every source."""
        if self.daily_at is not None:
            return next_daily_run(after, self.daily_at, self.timezone)
        return after + timedelta(seconds=interval)

    def _is_due(self, source: JobSource, now: datetime, force: bool) -> bool:
        if force:
            # A restart loop must not hammer the source: skip recent runs.
            return source.last_run_at is None or source.last_run_at <= now - self.startup_min_gap
        return source.next_run_at is None or source.next_run_at <= now

    def run_due(
        self, *, now: datetime | None = None, limit: int = 10, force: bool = False
    ) -> tuple[PollOutcome, ...]:
        """Poll due sources; ``force`` polls enabled sources before they are due."""
        if type(limit) is not int or limit <= 0:
            raise ValueError("source batch limit must be a positive integer")
        due_at = now or self.clock()
        due = (
            or_(
                JobSource.last_run_at.is_(None),
                JobSource.last_run_at <= due_at - self.startup_min_gap,
            )
            if force
            else or_(JobSource.next_run_at.is_(None), JobSource.next_run_at <= due_at)
        )
        with self.sessions() as session:
            identifiers = session.scalars(
                select(JobSource.id)
                .where(JobSource.enabled.is_(True), due)
                .order_by(JobSource.next_run_at.asc().nullsfirst(), JobSource.id)
                .limit(limit)
            ).all()
        outcomes = []
        for source_id in identifiers:
            with source_lock(self.engine, source_id) as acquired:
                if not acquired:
                    continue
                outcome = self._poll_source(source_id, now or self.clock(), force)
                if outcome is not None:
                    outcomes.append(outcome)
        return tuple(outcomes)

    def _poll_source(
        self, source_id: int, now: datetime, force: bool = False
    ) -> PollOutcome | None:
        with self.sessions() as session:
            source = session.get(JobSource, source_id)
            # Another worker may have completed this source before lock acquisition.
            if source is None or not source.enabled or not self._is_due(source, now, force):
                return None
            interval = interval_seconds(source.polling_interval, self.default_interval_seconds)
            poller = self.pollers.get(source.name.casefold())
            source.last_run_at = now
            source.next_run_at = self._next_run(now, interval)
            session.commit()
            if poller is None:
                status = "UNSUPPORTED"
            else:
                try:
                    result = poller(session, source_id)
                    status = result.status
                    if status not in ("SUCCEEDED", "PARTIAL", "FAILED"):
                        status = "FAILED"
                except Exception:
                    status = "FAILED"
                if status == "FAILED":
                    session.rollback()
            finished_at = self.clock()
            # Reload after a poller may have committed or rolled back its own work.
            source = session.get(JobSource, source_id, populate_existing=True)
            if source is not None:
                source.last_run_at = now
                source.next_run_at = self._next_run(finished_at, interval)
                if status == "SUCCEEDED":
                    source.last_success_at = finished_at
                    source.last_error = None
                else:
                    source.last_error = {
                        "PARTIAL": "partial_records",
                        "FAILED": "poll_failed",
                        "UNSUPPORTED": "unsupported_source",
                    }[status]
                session.commit()
            if status != "SUCCEEDED":
                logger.warning(
                    json.dumps(
                        {"event": "source_poll_result", "source_id": source_id, "status": status},
                        sort_keys=True,
                    )
                )
            return PollOutcome(source_id, status)
