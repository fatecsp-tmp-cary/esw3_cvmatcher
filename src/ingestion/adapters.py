"""Source adapter contract and bounded, privacy-safe request policy."""

import math
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import Any, Protocol


class PollingMode(StrEnum):
    INCREMENTAL = "INCREMENTAL"
    SNAPSHOT = "SNAPSHOT"


class SourceAdapter(Protocol):
    """Transport/normalization boundary; raw values are transient source records.

    A source's declared polling mode alone never proves snapshot completeness.
    Ingestion must also establish successful complete coverage for that run.
    """

    platform: str
    polling_mode: PollingMode
    snapshot_complete: bool

    def discover(self) -> AsyncIterator[str]:
        """Yield stable source IDs; malformed discovery records fail explicitly."""

    def fetch_jobs(self) -> AsyncIterator[Any]:
        """Yield raw records, leaving per-record rejection to ingestion."""

    async def fetch_job(self, source_job_id: str) -> dict[str, Any] | None:
        """Read one source record; absence is not availability evidence."""

    def normalize(self, raw_job: Any) -> dict[str, Any]:
        """Map a source record to canonical source-supplied job values."""


class SourceError(RuntimeError):
    """A safe failure category without transport/body/URL exception messages."""

    def __init__(
        self, category: str, *, retryable: bool = False, retry_after: str | None = None
    ) -> None:
        super().__init__(category)
        self.category = category
        self.retryable = retryable
        self.retry_after = retry_after


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """At most three total requests and at most 60 seconds between attempts."""

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or not 1 <= self.max_attempts <= 3
        ):
            raise ValueError("max_attempts must be an integer between 1 and 3")
        if (
            not math.isfinite(self.base_delay_seconds)
            or not math.isfinite(self.max_delay_seconds)
            or not 0 <= self.base_delay_seconds <= self.max_delay_seconds <= 60
        ):
            raise ValueError("retry delays must be finite and between 0 and 60 seconds")

    def delay(self, failed_attempt: int, retry_after: str | None, now: datetime) -> float:
        fallback = min(self.base_delay_seconds * 2 ** (failed_attempt - 1), self.max_delay_seconds)
        if retry_after is None:
            return fallback
        try:
            # RFC Retry-After is an integer delay or an HTTP date, never a float.
            if retry_after.isascii() and retry_after.isdigit():
                delay = float(int(retry_after))
            else:
                parsed = parsedate_to_datetime(retry_after)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                delay = (parsed - now).total_seconds()
            return min(max(delay, 0.0), self.max_delay_seconds)
        except (ValueError, TypeError, OverflowError):
            return fallback
