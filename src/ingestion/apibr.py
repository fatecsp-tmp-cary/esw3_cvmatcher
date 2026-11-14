"""Sequential APiBR polling with source-run evidence and safe job upserts."""

import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import func, select, update
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from src.ingestion.adapters import PollingMode, RetryPolicy, SourceError
from src.ingestion.completeness import SnapshotAttestation
from src.ingestion.upsert import upsert_job
from src.normalization.jobs.apibr import normalize_apibr_job
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun

_APIBR_ISSUES_URL = "https://apibr.com/vagas/api/v2/issues"
_PAGE_SIZE = 100
_REQUEST_TIMEOUT_SECONDS = 15
_MAX_PAGES = 1000


class IssuePageClient(Protocol):
    def fetch_page(self, page: int) -> list[Any]:
        """Return one APiBR issues page or raise when the response is invalid."""


class APiBRClient:
    """Bounded synchronous APiBR page transport, also usable by async adapters."""

    def __init__(
        self,
        *,
        transport: Callable[[Request, int], bytes] | None = None,
        retry_policy: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.transport = transport or self._read_response
        self.retry_policy = retry_policy or RetryPolicy()
        self.sleep = sleep
        self.now = now
        self.request_failures = 0

    @staticmethod
    def _read_response(request: Request, timeout: int) -> bytes:
        with urlopen(request, timeout=timeout) as response:
            return response.read()

    def request_page(self, page: int) -> list[Any]:
        """Perform one request; errors expose categories, never upstream text."""
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError("page must be a positive integer")
        query = urlencode({"per_page": _PAGE_SIZE, "page": page, "includeBody": "true"})
        payload = self._request_json(f"{_APIBR_ISSUES_URL}?{query}")
        if not isinstance(payload, list):
            self.request_failures += 1
            raise SourceError("invalid_page")
        return payload

    def _request_json(self, url: str):
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "cv-match-job-ingestor"},
        )
        try:
            raw = self.transport(request, _REQUEST_TIMEOUT_SECONDS)
        except HTTPError as error:
            self.request_failures += 1
            retryable = error.code == 429 or 500 <= error.code <= 599
            category = (
                "http_rate_limit"
                if error.code == 429
                else "http_server_failure"
                if retryable
                else "http_permanent_failure"
            )
            retry_after = error.headers.get("Retry-After") if error.headers is not None else None
            error.close()
            raise SourceError(category, retryable=retryable, retry_after=retry_after) from None
        except (URLError, OSError):
            self.request_failures += 1
            raise SourceError("transport_failure", retryable=True) from None
        except Exception:
            self.request_failures += 1
            raise SourceError("transport_failure") from None
        try:
            payload = json.loads(raw)
        except (ValueError, TypeError, UnicodeError):
            self.request_failures += 1
            raise SourceError("invalid_page") from None
        return payload

    def fetch_health(self):
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                return self._request_json("https://apibr.com/vagas/api/v2/health")
            except SourceError as error:
                if not error.retryable or attempt == self.retry_policy.max_attempts:
                    raise
                self.sleep(self.retry_policy.delay(attempt, error.retry_after, self.now()))
        raise AssertionError("unreachable retry state")

    def fetch_page(self, page: int) -> list[Any]:
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                return self.request_page(page)
            except SourceError as error:
                if not error.retryable or attempt == self.retry_policy.max_attempts:
                    raise
                self.sleep(self.retry_policy.delay(attempt, error.retry_after, self.now()))
        raise AssertionError("unreachable retry state")


class APiBRAdapter:
    """Async common source interface without hidden GitHub availability requests.

    All records are returned unchanged for ingestion's independent normalization
    and rejection. Reaching an empty page does not prove snapshot completeness.
    """

    platform = "apibr"
    polling_mode = PollingMode.INCREMENTAL
    snapshot_complete = False

    def __init__(
        self,
        client: APiBRClient | None = None,
        *,
        max_pages: int = _MAX_PAGES,
        sleep: Callable[[float], Any] = asyncio.sleep,
        polling_mode: PollingMode = PollingMode.INCREMENTAL,
    ) -> None:
        if (
            isinstance(max_pages, bool)
            or not isinstance(max_pages, int)
            or not 1 <= max_pages <= _MAX_PAGES
        ):
            raise ValueError("max_pages must be between 1 and the page safety limit")
        self.client = client or APiBRClient()
        self.max_pages = max_pages
        self.sleep = sleep
        self.polling_mode = PollingMode(polling_mode)
        self.snapshot_evidence: dict | None = None

    async def _fetch_page(self, page: int) -> list[Any]:
        policy = self.client.retry_policy
        for attempt in range(1, policy.max_attempts + 1):
            try:
                # Only the bounded blocking HTTP operation runs in a thread;
                # retry waits remain cancellable in the event loop.
                return await asyncio.to_thread(self.client.request_page, page)
            except SourceError as error:
                if not error.retryable or attempt == policy.max_attempts:
                    raise
                await self.sleep(policy.delay(attempt, error.retry_after, self.client.now()))
        raise AssertionError("unreachable retry state")

    async def fetch_jobs(self) -> AsyncIterator[Any]:
        self.snapshot_complete = False
        self.snapshot_evidence = None
        attestation = (
            SnapshotAttestation(self.client) if self.polling_mode == PollingMode.SNAPSHOT else None
        )
        rejections = 0
        if attestation is not None:
            await asyncio.to_thread(attestation.begin)
        for page in range(1, self.max_pages + 1):
            records = await self._fetch_page(page)
            if not records:
                break
            for record in records:
                if attestation is not None:
                    attestation.observe(record)
                    try:
                        self.normalize(record)
                    except (TypeError, ValueError):
                        rejections += 1
                yield record
        else:
            raise SourceError("page_safety_limit")
        if attestation is not None:
            evidence = await asyncio.to_thread(
                attestation.finish,
                rejections=rejections,
                terminal_empty=True,
            )
            self.snapshot_evidence = evidence
            self.snapshot_complete = evidence["qualified"] is True

    async def discover(self) -> AsyncIterator[str]:
        async for record in self.fetch_jobs():
            if not isinstance(record, dict):
                raise SourceError("invalid_discovery_record")
            identity = record.get("id")
            if (
                isinstance(identity, bool)
                or not isinstance(identity, (int, str))
                or not str(identity).strip()
            ):
                raise SourceError("invalid_discovery_record")
            yield str(identity).strip()

    async def fetch_job(self, source_job_id: str) -> dict[str, Any] | None:
        if not isinstance(source_job_id, str) or not source_job_id.strip():
            raise ValueError("source_job_id must be a nonempty string")
        async for record in self.fetch_jobs():
            if isinstance(record, dict):
                identity = record.get("id")
                if (
                    not isinstance(identity, bool)
                    and isinstance(identity, (int, str))
                    and str(identity).strip() == source_job_id.strip()
                ):
                    return record
        return None

    def normalize(self, raw_job: Any) -> dict[str, Any]:
        return normalize_apibr_job(raw_job)


def iter_apibr_issues(client: IssuePageClient) -> Iterator[Any]:
    """Yield pages sequentially; the observed end does not prove completeness."""
    for page in range(1, _MAX_PAGES + 1):
        issues = client.fetch_page(page)
        if not issues:
            return
        yield from issues
    raise RuntimeError("APiBR scan exceeded the configured page safety limit")


@dataclass(frozen=True, slots=True)
class APiBRRunResult:
    run_id: int
    status: str
    snapshot_complete: bool
    jobs_found: int
    jobs_created: int
    jobs_updated: int
    jobs_unchanged: int
    jobs_expired: int
    jobs_reactivated: int
    jobs_rejected: int
    jobs_absent: int = 0
    jobs_marked_stale: int = 0


def _mark_absent_stale(session: Session, source_id: int, scan_started: datetime) -> tuple[int, int]:
    """Mark this source's ACTIVE jobs not observed since ``scan_started`` as STALE.

    Callers must have established a qualifying snapshot (ADR-015). Returns the
    non-expired absent job count and the number newly marked STALE.
    """
    absent = (
        Job.source_id == source_id,
        Job.platform == "apibr",
        Job.last_seen_at < scan_started,
    )
    absent_count = session.scalar(
        select(func.count()).select_from(Job).where(*absent, Job.status != JobStatus.EXPIRED)
    )
    marked = session.execute(
        update(Job)
        .where(*absent, Job.status == JobStatus.ACTIVE)
        .values(status=JobStatus.STALE)
        .returning(Job.id)
        .execution_options(synchronize_session=False)
    ).all()
    return int(absent_count or 0), len(marked)


def _normalize_issue(raw: Any) -> tuple[dict[str, Any], bool]:
    # Every record observed in the listing carries availability evidence (ADR-014).
    return normalize_apibr_job(raw), True


def ingest_apibr(
    session: Session,
    source_id: int,
    client: IssuePageClient | None = None,
    *,
    started_at: datetime | None = None,
) -> APiBRRunResult:
    """Persist valid records, rejecting malformed jobs in isolated savepoints.

    SNAPSHOT configurations may attest the approved best-effort health/count
    conditions. Absence-based lifecycle changes remain disabled. Polling
    failures roll back all job updates. Rejected records produce a PARTIAL run;
    errors contain counts or exception types, never source response text.
    """
    source = session.get(JobSource, source_id)
    if source is None:
        raise ValueError("APiBR source was not found")

    client = client or APiBRClient()
    started_at = started_at or datetime.now(UTC)
    run: SourceRun | None = SourceRun(
        source_id=source_id,
        started_at=started_at,
        status="RUNNING",
        snapshot_complete=False,
        polling_mode=source.polling_mode,
    )
    session.add(run)
    session.commit()
    assert run is not None
    run_id = run.id
    timer_started = time.perf_counter()
    # Observations use the real clock, so absence is measured against it as well.
    scan_started = datetime.now(UTC)
    absent = marked_stale = 0

    counts = {
        "found": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "expired": 0,
        "reactivated": 0,
        "rejected": 0,
    }
    attestation = SnapshotAttestation(client) if source.polling_mode == "SNAPSHOT" else None
    try:
        if attestation is not None:
            attestation.begin()
        for raw_issue in iter_apibr_issues(client):
            counts["found"] += 1
            if attestation is not None:
                attestation.observe(raw_issue)
            try:
                with session.begin_nested():
                    normalized, verified = _normalize_issue(raw_issue)
                    outcome, expired, reactivated = upsert_job(
                        session, source_id, normalized, datetime.now(UTC), verified
                    )
                    session.flush()
            except (ValueError, DataError, IntegrityError):
                counts["rejected"] += 1
                continue
            counts[outcome] += 1
            counts["expired"] += int(expired)
            counts["reactivated"] += int(reactivated)

        finished_at = datetime.now(UTC)
        run = session.get(SourceRun, run_id)
        source = session.get(JobSource, source_id)
        if run is None or source is None:
            raise RuntimeError("Source execution state is unavailable")
        status = "PARTIAL" if counts["rejected"] else "SUCCEEDED"
        if attestation is not None:
            run.snapshot_evidence = attestation.finish(
                rejections=counts["rejected"],
                terminal_empty=True,
            )
            run.snapshot_complete = status == "SUCCEEDED" and run.snapshot_evidence["qualified"]
            if run.snapshot_complete:
                # Only a qualifying snapshot makes absence meaningful (ADR-015).
                absent, marked_stale = _mark_absent_stale(session, source_id, scan_started)
        run.status = status
        run.finished_at = finished_at
        run.duration_ms = int((time.perf_counter() - timer_started) * 1000)
        run.jobs_found = counts["found"]
        run.jobs_created = counts["created"]
        run.jobs_updated = counts["updated"]
        run.jobs_unchanged = counts["unchanged"]
        run.jobs_expired = counts["expired"]
        run.jobs_reactivated = counts["reactivated"]
        run.jobs_rejected = counts["rejected"]
        run.errors = f"RejectedRecords:{counts['rejected']}" if counts["rejected"] else None
        run.jobs_absent = absent
        run.jobs_marked_stale = marked_stale
        source.last_run_at = started_at
        if status == "SUCCEEDED":
            source.last_success_at = finished_at
        source.last_error = run.errors
        session.commit()
    except Exception as error:
        session.rollback()
        absent = marked_stale = 0
        failed_at = datetime.now(UTC)
        run = session.get(SourceRun, run_id)
        source = session.get(JobSource, source_id)
        if run is not None:
            run.status = "FAILED"
            run.finished_at = failed_at
            run.duration_ms = int((time.perf_counter() - timer_started) * 1000)
            run.jobs_found = counts["found"]
            run.jobs_created = 0
            run.jobs_updated = 0
            run.jobs_unchanged = 0
            run.jobs_expired = 0
            run.jobs_reactivated = 0
            run.jobs_rejected = counts["rejected"]
            run.errors = type(error).__name__
        if source is not None:
            source.last_run_at = started_at
            source.last_error = type(error).__name__
        session.commit()
        raise

    return APiBRRunResult(
        run_id=run_id,
        status=status,
        snapshot_complete=run.snapshot_complete,
        jobs_found=counts["found"],
        jobs_created=counts["created"],
        jobs_updated=counts["updated"],
        jobs_unchanged=counts["unchanged"],
        jobs_expired=counts["expired"],
        jobs_reactivated=counts["reactivated"],
        jobs_rejected=counts["rejected"],
        jobs_absent=absent,
        jobs_marked_stale=marked_stale,
    )
