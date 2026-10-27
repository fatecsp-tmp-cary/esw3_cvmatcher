"""Sequential APiBR polling with source-run evidence and safe job upserts."""

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from src.ingestion.upsert import upsert_job
from src.normalization.jobs.apibr import normalize_apibr_job
from src.normalization.jobs.apibr_status import check_apibr_job_status
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun

_APIBR_ISSUES_URL = "https://apibr.com/vagas/api/v2/issues"
_PAGE_SIZE = 100
_REQUEST_TIMEOUT_SECONDS = 15
_MAX_PAGES = 1000


class IssuePageClient(Protocol):
    def fetch_page(self, page: int) -> list[dict[str, Any]]:
        """Return one APiBR issues page or raise when the response is invalid."""


class APiBRClient:
    """Read APiBR issue pages one at a time until the first empty page."""

    def fetch_page(self, page: int) -> list[dict[str, Any]]:
        query = urlencode({"per_page": _PAGE_SIZE, "page": page, "includeBody": "true"})
        request = Request(
            f"{_APIBR_ISSUES_URL}?{query}",
            headers={"Accept": "application/json", "User-Agent": "cv-match-job-ingestor"},
        )
        with urlopen(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read())

        if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
            raise ValueError("APiBR returned an invalid issues page")
        return payload


def iter_apibr_issues(client: IssuePageClient) -> Iterator[dict[str, Any]]:
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


def _normalize_issue(raw: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    job = normalize_apibr_job(raw)
    state = raw.get("state")
    if isinstance(state, str) and state in {"open", "closed"}:
        return job, True

    verified_status = check_apibr_job_status(job.get("job_url"))
    if verified_status is None:
        return job, False
    job["status"] = verified_status.value
    return job, True


def ingest_apibr(
    session: Session,
    source_id: int,
    client: IssuePageClient | None = None,
    *,
    started_at: datetime | None = None,
) -> APiBRRunResult:
    """Poll APiBR and atomically persist jobs and the corresponding run record.

    The scan is always recorded as incomplete because the source scan has not
    been proven complete. Therefore it never marks absent jobs STALE. Polling
    failures roll back all job updates and persist a failed run with only the
    exception type, not potentially sensitive response text.
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
    }
    try:
        for raw_issue in iter_apibr_issues(client):
            normalized, verified = _normalize_issue(raw_issue)
            counts["found"] += 1
            outcome, expired, reactivated = upsert_job(
                session,
                source_id,
                normalized,
                datetime.now(UTC),
                verified,
            )
            counts[outcome] += 1
            counts["expired"] += int(expired)
            counts["reactivated"] += int(reactivated)

        finished_at = datetime.now(UTC)
        run = session.get(SourceRun, run_id)
        source = session.get(JobSource, source_id)
        run.status = "SUCCEEDED"
        run.finished_at = finished_at
        run.duration_ms = int((time.perf_counter() - timer_started) * 1000)
        run.jobs_found = counts["found"]
        run.jobs_created = counts["created"]
        run.jobs_updated = counts["updated"]
        run.jobs_unchanged = counts["unchanged"]
        run.jobs_expired = counts["expired"]
        run.jobs_reactivated = counts["reactivated"]
        run.jobs_absent = 0
        run.jobs_marked_stale = 0
        source.last_run_at = started_at
        source.last_success_at = finished_at
        source.last_error = None
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
            run.errors = type(error).__name__
        if source is not None:
            source.last_run_at = started_at
            source.last_error = type(error).__name__
        session.commit()
        raise

    return APiBRRunResult(
        run_id=run_id,
        status="SUCCEEDED",
        snapshot_complete=False,
        jobs_found=counts["found"],
        jobs_created=counts["created"],
        jobs_updated=counts["updated"],
        jobs_unchanged=counts["unchanged"],
        jobs_expired=counts["expired"],
        jobs_reactivated=counts["reactivated"],
    )
