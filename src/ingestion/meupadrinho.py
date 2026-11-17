"""MeuPadrinho source adapter, JSONL ingestion, and bounded availability validation."""

import asyncio
import json
import time
from collections.abc import AsyncIterator, Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from src.ingestion.adapters import PollingMode, RateLimiter, RetryPolicy, SourceError
from src.ingestion.upsert import lock_job_identities, upsert_job
from src.normalization.jobs.meupadrinho import normalize_meupadrinho_job
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun

_MEUPADRINHO_LIST_URL = "https://meupadrinho.com.br/api/vagas"
_MEUPADRINHO_DETAIL_URL = "https://meupadrinho.com.br/api/vagas/{nano_id}"
_REQUEST_TIMEOUT_SECONDS = 15
_DEFAULT_VALIDATION_LIMIT = 50
_MAX_VALIDATION_LIMIT = 500
_MAX_DISCOVERY_FETCH_LIMIT = 500
MEUPADRINHO_MAX_REQUESTS_PER_SECOND = 60.0


class MeuPadrinhoDetailClient(Protocol):
    def fetch_job(self, nano_id: str) -> dict[str, Any] | None:
        """Return the raw detail object for ``nano_id``, or ``None`` if HTTP 404."""


class MeuPadrinhoClient:
    """Bounded synchronous MeuPadrinho HTTP client, also usable by async adapters."""

    def __init__(
        self,
        *,
        transport: Callable[[Request, int], bytes] | None = None,
        retry_policy: RetryPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.transport = transport or self._read_response
        self.retry_policy = retry_policy or RetryPolicy(jitter_ratio=0.2)
        self.rate_limiter = rate_limiter or RateLimiter(MEUPADRINHO_MAX_REQUESTS_PER_SECOND)
        self.sleep = sleep
        self.now = now
        self.request_failures = 0

    @staticmethod
    def _read_response(request: Request, timeout: int) -> bytes:
        with urlopen(request, timeout=timeout) as response:
            if getattr(response, "status", 200) == 204:
                return b""
            return response.read()

    def _request_json(
        self,
        url: str,
        *,
        allow_404: bool = False,
        allow_empty: bool = False,
        pace: bool = True,
    ) -> Any:
        if pace and self.rate_limiter is not None:
            self.rate_limiter.wait(self.sleep)
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "cv-match-job-ingestor"},
        )
        try:
            raw = self.transport(request, _REQUEST_TIMEOUT_SECONDS)
        except HTTPError as error:
            if allow_404 and error.code == 404:
                error.close()
                return None
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

        if allow_empty and (raw == b"" or not raw.strip()):
            return {"vagas": []}
        try:
            return json.loads(raw)
        except (ValueError, TypeError, UnicodeError):
            self.request_failures += 1
            raise SourceError("invalid_page") from None

    def request_listing(
        self, params: dict[str, str] | None = None, *, pace: bool = True
    ) -> list[Any]:
        url = _MEUPADRINHO_LIST_URL
        if params:
            url = f"{url}?{urlencode(params)}"
        payload = self._request_json(url, allow_empty=True, pace=pace)
        if isinstance(payload, dict) and isinstance(payload.get("vagas"), list):
            return payload["vagas"]
        if isinstance(payload, list):
            return payload
        self.request_failures += 1
        raise SourceError("invalid_page")

    def fetch_listing(self, params: dict[str, str] | None = None) -> list[Any]:
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                return self.request_listing(params)
            except SourceError as error:
                if not error.retryable or attempt == self.retry_policy.max_attempts:
                    raise
                self.sleep(self.retry_policy.delay(attempt, error.retry_after, self.now()))
        raise AssertionError("unreachable retry state")

    def request_job(self, nano_id: str, *, pace: bool = True) -> dict[str, Any] | None:
        if not isinstance(nano_id, str) or not nano_id.strip():
            raise ValueError("nano_id must be a nonempty string")
        clean_id = nano_id.strip()
        url = _MEUPADRINHO_DETAIL_URL.format(nano_id=quote(clean_id, safe=""))
        payload = self._request_json(url, allow_404=True, pace=pace)
        if payload is None:
            return None
        if not isinstance(payload, dict):
            self.request_failures += 1
            raise SourceError("invalid_page")
        return {"nano_id": clean_id, "contents": payload}

    def fetch_job(self, nano_id: str) -> dict[str, Any] | None:
        if not isinstance(nano_id, str) or not nano_id.strip():
            raise ValueError("nano_id must be a nonempty string")
        for attempt in range(1, self.retry_policy.max_attempts + 1):
            try:
                return self.request_job(nano_id)
            except SourceError as error:
                if not error.retryable or attempt == self.retry_policy.max_attempts:
                    raise
                self.sleep(self.retry_policy.delay(attempt, error.retry_after, self.now()))
        raise AssertionError("unreachable retry state")


class MeuPadrinhoAdapter:
    """Async common source interface for MeuPadrinho."""

    platform = "meupadrinho"
    polling_mode = PollingMode.INCREMENTAL
    snapshot_complete = False

    def __init__(
        self,
        client: MeuPadrinhoClient | None = None,
        *,
        sleep: Callable[[float], Any] = asyncio.sleep,
        listing_queries: Sequence[dict[str, str]] | None = None,
    ) -> None:
        self.client = client or MeuPadrinhoClient()
        self.sleep = sleep
        self.listing_queries = tuple(listing_queries) if listing_queries is not None else ({},)

    async def _pace(self) -> None:
        if self.client.rate_limiter is not None:
            delay = self.client.rate_limiter.acquire_delay()
            if delay > 0.0:
                await self.sleep(delay)

    async def _fetch_listing(self, params: dict[str, str]) -> list[Any]:
        policy = self.client.retry_policy
        for attempt in range(1, policy.max_attempts + 1):
            try:
                await self._pace()
                return await asyncio.to_thread(self.client.request_listing, params, pace=False)
            except SourceError as error:
                if not error.retryable or attempt == policy.max_attempts:
                    raise
                await self.sleep(policy.delay(attempt, error.retry_after, self.client.now()))
        raise AssertionError("unreachable retry state")

    async def _fetch_detail(self, nano_id: str) -> dict[str, Any] | None:
        policy = self.client.retry_policy
        for attempt in range(1, policy.max_attempts + 1):
            try:
                await self._pace()
                return await asyncio.to_thread(self.client.request_job, nano_id, pace=False)
            except SourceError as error:
                if not error.retryable or attempt == policy.max_attempts:
                    raise
                await self.sleep(policy.delay(attempt, error.retry_after, self.client.now()))
        raise AssertionError("unreachable retry state")

    async def discover(self) -> AsyncIterator[str]:
        self.snapshot_complete = False
        seen: set[str] = set()
        for query in self.listing_queries:
            records = await self._fetch_listing(query)
            for record in records:
                if not isinstance(record, dict):
                    raise SourceError("invalid_discovery_record")
                identity = record.get("nano_id") or record.get("id")
                if (
                    isinstance(identity, bool)
                    or not isinstance(identity, (int, str))
                    or not str(identity).strip()
                ):
                    raise SourceError("invalid_discovery_record")
                clean_id = str(identity).strip()
                if clean_id not in seen:
                    seen.add(clean_id)
                    yield clean_id

    async def fetch_jobs(self) -> AsyncIterator[Any]:
        self.snapshot_complete = False
        async for nano_id in self.discover():
            detail = await self._fetch_detail(nano_id)
            if detail is not None:
                yield detail

    async def fetch_job(self, source_job_id: str) -> dict[str, Any] | None:
        if not isinstance(source_job_id, str) or not source_job_id.strip():
            raise ValueError("source_job_id must be a nonempty string")
        return await self._fetch_detail(source_job_id.strip())

    def normalize(self, raw_job: Any) -> dict[str, Any]:
        return normalize_meupadrinho_job(raw_job)


@dataclass(frozen=True, slots=True)
class MeuPadrinhoRunResult:
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


def ingest_meupadrinho_records(
    session: Session,
    source_id: int,
    records: Iterable[Any],
    *,
    started_at: datetime | None = None,
) -> MeuPadrinhoRunResult:
    """Persist normalized MeuPadrinho records with isolated savepoints and SourceRun tracking."""
    source = session.get(JobSource, source_id)
    if source is None:
        raise ValueError("MeuPadrinho source was not found")

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
        observations: list[tuple[dict[str, Any], bool, datetime]] = []
        for raw_record in records:
            counts["found"] += 1
            if isinstance(raw_record, (str, bytes)):
                try:
                    raw_record = json.loads(raw_record)
                except (ValueError, TypeError, UnicodeError):
                    counts["rejected"] += 1
                    continue
            try:
                normalized = normalize_meupadrinho_job(raw_record)
            except (TypeError, ValueError):
                counts["rejected"] += 1
                continue
            observations.append((normalized, True, datetime.now(UTC)))

        lock_job_identities(
            session,
            ((job["platform"], job["source_job_id"]) for job, _, _ in observations),
        )
        for normalized, verified, observed_at in observations:
            try:
                with session.begin_nested():
                    outcome, expired, reactivated = upsert_job(
                        session, source_id, normalized, observed_at, verified
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
        if counts["found"] > 0 and counts["rejected"] == counts["found"]:
            status = "FAILED"
        else:
            status = "PARTIAL" if counts["rejected"] else "SUCCEEDED"
        run.status = status
        run.snapshot_complete = False
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

    return MeuPadrinhoRunResult(
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
        jobs_absent=0,
        jobs_marked_stale=0,
    )


def ingest_meupadrinho_jsonl(
    session: Session,
    source_id: int,
    path: str | Path,
    *,
    started_at: datetime | None = None,
) -> MeuPadrinhoRunResult:
    """Ingest a JSONL dump generated by the MeuPadrinho script (`meu_padriho.sh`)."""
    file_path = Path(path)
    if not file_path.is_file():
        raise ValueError("MeuPadrinho JSONL file was not found")

    def _iter_lines() -> Iterable[str]:
        with file_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    yield stripped

    return ingest_meupadrinho_records(session, source_id, _iter_lines(), started_at=started_at)


def ingest_meupadrinho(
    session: Session,
    source_id: int,
    client: MeuPadrinhoClient | None = None,
    *,
    started_at: datetime | None = None,
    validation_limit: int = _DEFAULT_VALIDATION_LIMIT,
    discover_new: bool = False,
    listing_queries: Sequence[dict[str, str]] | None = None,
) -> MeuPadrinhoRunResult:
    """Validate persisted non-expired MeuPadrinho jobs and optionally discover new ones.

    Active/discovered/stale jobs for ``platform == 'meupadrinho'`` are checked in
    bounded batches ordered by oldest ``last_verified_at`` (nulls first).
    - If ``GET /api/vagas/{nano_id}`` returns ``vaga_encerrada=True``, the job transitions
      to ``EXPIRED`` via ``upsert_job``.
    - If ``GET /api/vagas/{nano_id}`` returns HTTP 404 (``None``), the job is explicitly
      marked ``EXPIRED``.
    - If ``discover_new`` is enabled, listings are queried first and unseen ``nano_id``s
      are fetched and ingested in the same bounded run.
    """
    if (
        isinstance(validation_limit, bool)
        or not isinstance(validation_limit, int)
        or not 1 <= validation_limit <= _MAX_VALIDATION_LIMIT
    ):
        raise ValueError("validation_limit must be between 1 and the validation safety limit")

    source = session.get(JobSource, source_id)
    if source is None:
        raise ValueError("MeuPadrinho source was not found")

    client = client or MeuPadrinhoClient()
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
        candidates = session.scalars(
            select(Job.source_job_id)
            .where(
                Job.source_id == source_id,
                Job.platform == "meupadrinho",
                Job.status != JobStatus.EXPIRED,
            )
            .order_by(Job.last_verified_at.asc().nullsfirst(), Job.id.asc())
            .limit(validation_limit)
        ).all()

        target_ids: list[str] = list(candidates)
        seen_ids: set[str] = set(target_ids)

        if discover_new:
            queries = tuple(listing_queries) if listing_queries is not None else ({},)
            discovered_count = 0
            for query in queries:
                for item in client.fetch_listing(query):
                    if not isinstance(item, dict):
                        counts["found"] += 1
                        counts["rejected"] += 1
                        continue
                    raw_id = item.get("nano_id") or item.get("id")
                    if (
                        isinstance(raw_id, bool)
                        or not isinstance(raw_id, (int, str))
                        or not str(raw_id).strip()
                    ):
                        counts["found"] += 1
                        counts["rejected"] += 1
                        continue
                    clean_id = str(raw_id).strip()
                    if clean_id not in seen_ids:
                        seen_ids.add(clean_id)
                        target_ids.append(clean_id)
                        discovered_count += 1
                        if discovered_count >= _MAX_DISCOVERY_FETCH_LIMIT:
                            break
                if discovered_count >= _MAX_DISCOVERY_FETCH_LIMIT:
                    break

        observations: list[tuple[dict[str, Any], bool, datetime]] = []
        missing_ids: list[tuple[str, datetime]] = []
        detail_failures = 0
        last_detail_error: SourceError | None = None

        for nano_id in target_ids:
            counts["found"] += 1
            try:
                raw_detail = client.fetch_job(nano_id)
            except SourceError as error:
                detail_failures += 1
                counts["rejected"] += 1
                last_detail_error = error
                continue
            observed_at = datetime.now(UTC)
            if raw_detail is None:
                missing_ids.append((nano_id, observed_at))
                continue
            try:
                normalized = normalize_meupadrinho_job(raw_detail)
            except (TypeError, ValueError):
                counts["rejected"] += 1
                continue
            observations.append((normalized, True, observed_at))

        if target_ids and detail_failures == len(target_ids) and last_detail_error is not None:
            raise last_detail_error

        all_identities = [
            *((job["platform"], job["source_job_id"]) for job, _, _ in observations),
            *(("meupadrinho", nano_id) for nano_id, _ in missing_ids),
        ]
        if all_identities:
            lock_job_identities(session, all_identities)

        for normalized, verified, observed_at in observations:
            try:
                with session.begin_nested():
                    outcome, expired, reactivated = upsert_job(
                        session, source_id, normalized, observed_at, verified
                    )
                    session.flush()
            except (ValueError, DataError, IntegrityError):
                counts["rejected"] += 1
                continue
            counts[outcome] += 1
            counts["expired"] += int(expired)
            counts["reactivated"] += int(reactivated)

        for nano_id, observed_at in missing_ids:
            existing = session.scalar(
                select(Job)
                .where(Job.platform == "meupadrinho", Job.source_job_id == nano_id)
                .execution_options(populate_existing=True)
            )
            if existing is not None and existing.status != JobStatus.EXPIRED:
                existing.status = JobStatus.EXPIRED
                existing.last_verified_at = observed_at
                counts["unchanged"] += 1
                counts["expired"] += 1

        finished_at = datetime.now(UTC)
        run = session.get(SourceRun, run_id)
        source = session.get(JobSource, source_id)
        if run is None or source is None:
            raise RuntimeError("Source execution state is unavailable")
        if counts["found"] > 0 and counts["rejected"] == counts["found"]:
            status = "FAILED"
        else:
            status = "PARTIAL" if counts["rejected"] else "SUCCEEDED"
        run.status = status
        run.snapshot_complete = False
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

    return MeuPadrinhoRunResult(
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
        jobs_absent=0,
        jobs_marked_stale=0,
    )
