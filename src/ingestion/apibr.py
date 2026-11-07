"""Sequential APiBR polling with source-run evidence and safe job upserts."""

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from src.ingestion.upsert import upsert_job
from src.normalization.jobs.apibr import normalize_apibr_job
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
    """Read APiBR issue pages one at a time until the first empty page."""

    def fetch_page(self, page: int) -> list[Any]:
        query = urlencode({"per_page": _PAGE_SIZE, "page": page, "includeBody": "true"})
        request = Request(
            f"{_APIBR_ISSUES_URL}?{query}",
            headers={"Accept": "application/json", "User-Agent": "cv-match-job-ingestor"},
        )
        with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())

        if not isinstance(payload, list):
            raise ValueError("APiBR returned an invalid issues page")
        return payload


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


def _normalize_issue(raw: Any) -> tuple[dict[str, Any], bool]:
    job = normalize_apibr_job(raw)
    return job, raw.get("state") in ("open", "closed")


def ingest_apibr(
    session: Session,
    source_id: int,
    client: IssuePageClient | None = None,
    *,
    started_at: datetime | None = None,
) -> APiBRRunResult:
    """Persist valid records, rejecting malformed jobs in isolated savepoints.

    The scan is always recorded as incomplete because the source scan has not
    been proven complete. Therefore it never marks absent jobs STALE. Polling
    failures roll back all job updates. Rejected records produce a PARTIAL run;
    errors contain counts or exception types, never source response text.
    """
    source = session.get(JobSource, source_id)
    if source is None:
        raise ValueError("APiBR source was not found")

    client = client or APiBRClient()
    started_at = started_at or datetime.now(UTC)
    run = SourceRun(
        source_id=source_id,
        started_at=started_at,
        status="RUNNING",
        snapshot_complete=False,
        polling_mode=source.polling_mode,
    )
    session.add(run)
    session.commit()
    run_id = run.id
    timer_started = time.perf_counter()

    counts = {
        "found": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "expired": 0,
        "reactivated": 0,
        "rejected": 0,
    }
    try:
        for raw_issue in iter_apibr_issues(client):
            counts["found"] += 1
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
        status = "PARTIAL" if counts["rejected"] else "SUCCEEDED"
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
        run.jobs_absent = 0
        run.jobs_marked_stale = 0
        source.last_run_at = started_at
        if status == "SUCCEEDED":
            source.last_success_at = finished_at
        source.last_error = run.errors
        session.commit()
    except Exception as error:
        session.rollback()
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
        snapshot_complete=False,
        jobs_found=counts["found"],
        jobs_created=counts["created"],
        jobs_updated=counts["updated"],
        jobs_unchanged=counts["unchanged"],
        jobs_expired=counts["expired"],
        jobs_reactivated=counts["reactivated"],
        jobs_rejected=counts["rejected"],
    )
