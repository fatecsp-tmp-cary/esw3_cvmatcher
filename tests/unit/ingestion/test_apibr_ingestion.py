import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.ingestion import apibr as apibr_ingestion
from src.ingestion.apibr import APiBRClient, ingest_apibr, iter_apibr_issues
from src.persistence.base import Base
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun


class _Pages:
    def __init__(self, *pages):
        self.pages = iter(pages)

    def fetch_page(self, _page: int):
        result = next(self.pages)
        if isinstance(result, BaseException):
            raise result
        return result


class _Response:
    def __init__(self, payload: list[dict]) -> None:
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return self._payload


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(JobSource(name="APiBR", type="api", polling_mode="sequential"))
        db.commit()
        yield db
    engine.dispose()


def _issue(issue_id: int, *, state: str = "open", body: str = "Build APIs") -> dict:
    return {
        "id": issue_id,
        "title": f"Developer {issue_id}",
        "state": state,
        "body": body,
        "html_url": f"https://github.com/acme/jobs/issues/{issue_id}",
    }


def test_apibr_client_uses_sequential_paged_issue_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return _Response([_issue(1)])

    monkeypatch.setattr(apibr_ingestion, "urlopen", fake_urlopen)
    page = APiBRClient().fetch_page(4)

    assert page[0]["id"] == 1
    assert calls[0][0].full_url.endswith("per_page=100&page=4&includeBody=true")
    assert calls[0][1] == 15


def test_apibr_page_iterator_stops_at_first_empty_page() -> None:
    client = _Pages([_issue(1)], [])

    assert list(iter_apibr_issues(client)) == [_issue(1)]


def test_apibr_page_iterator_fails_instead_of_assuming_completion_at_safety_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(apibr_ingestion, "_MAX_PAGES", 2)

    with pytest.raises(RuntimeError, match="safety limit"):
        list(iter_apibr_issues(_Pages([_issue(1)], [_issue(2)])))


def test_ingest_records_source_run_and_source_specific_statuses(session: Session) -> None:
    result = ingest_apibr(
        session,
        1,
        _Pages([_issue(1), _issue(2, state="closed")], []),
        started_at=datetime(2026, 10, 27, tzinfo=UTC),
    )

    jobs = session.scalars(select(Job).order_by(Job.source_job_id)).all()
    run = session.get(SourceRun, result.run_id)

    assert result.status == "SUCCEEDED"
    assert result.snapshot_complete is False
    assert result.jobs_found == 2
    assert result.jobs_created == 2
    assert result.jobs_expired == 1
    assert {job.status for job in jobs} == {JobStatus.ACTIVE, JobStatus.EXPIRED}
    assert run is not None
    assert run.jobs_absent == 0
    assert run.jobs_marked_stale == 0
    assert run.snapshot_complete is False


def test_ingest_updates_changed_content_and_preserves_unchanged_content_hash(
    session: Session,
) -> None:
    first = ingest_apibr(session, 1, _Pages([_issue(1)], []))
    job = session.scalar(select(Job).where(Job.source_job_id == "1"))
    original_hash = job.content_hash
    job.embedding = [0.1, 0.2]
    session.commit()

    unchanged = ingest_apibr(session, 1, _Pages([_issue(1)], []))
    assert unchanged.jobs_unchanged == 1
    assert job.content_hash == original_hash
    assert job.embedding == [0.1, 0.2]

    changed = ingest_apibr(session, 1, _Pages([_issue(1, body="Build better APIs")], []))
    assert changed.jobs_updated == 1
    assert job.content_hash != original_hash
    assert job.embedding is None
    assert first.run_id != changed.run_id


def test_incomplete_scan_never_marks_absent_jobs_stale(session: Session) -> None:
    now = datetime.now(UTC)
    session.add(
        Job(
            source_id=1,
            platform="apibr",
            source_job_id="old",
            title="Old job",
            status=JobStatus.STALE,
            first_seen_at=now - timedelta(days=1),
            last_seen_at=now - timedelta(days=1),
        )
    )
    session.commit()

    result = ingest_apibr(session, 1, _Pages([_issue(2)], []))

    old_job = session.scalar(select(Job).where(Job.source_job_id == "old"))
    run = session.get(SourceRun, result.run_id)
    assert old_job.status == JobStatus.STALE
    assert run.jobs_absent == 0
    assert run.jobs_marked_stale == 0


def test_ingest_reactivates_stale_jobs_when_an_open_issue_is_rediscovered(
    session: Session,
) -> None:
    ingest_apibr(session, 1, _Pages([_issue(1)], []))
    job = session.scalar(select(Job).where(Job.source_job_id == "1"))
    job.status = JobStatus.STALE
    session.commit()

    result = ingest_apibr(session, 1, _Pages([_issue(1)], []))

    assert job.status == JobStatus.ACTIVE
    assert result.jobs_reactivated == 1


def test_ingest_keeps_expired_jobs_expired_if_the_source_reopens_them(
    session: Session,
) -> None:
    ingest_apibr(session, 1, _Pages([_issue(1, state="closed")], []))

    result = ingest_apibr(session, 1, _Pages([_issue(1, state="open")], []))
    job = session.scalar(select(Job).where(Job.source_job_id == "1"))

    assert job.status == JobStatus.EXPIRED
    assert result.jobs_reactivated == 0


def test_ingest_uses_confirmed_url_status_when_issue_state_is_missing(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        apibr_ingestion,
        "check_apibr_job_status",
        lambda _url: JobStatus.EXPIRED,
    )
    issue = _issue(1)
    issue.pop("state")

    result = ingest_apibr(session, 1, _Pages([issue], []))
    job = session.scalar(select(Job).where(Job.source_job_id == "1"))

    assert result.jobs_expired == 1
    assert job.status == JobStatus.EXPIRED
    assert job.last_verified_at is not None


def test_ingest_does_not_verify_or_transition_on_an_unavailable_url_check(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(apibr_ingestion, "check_apibr_job_status", lambda _url: None)
    issue = _issue(1)
    issue.pop("state")

    ingest_apibr(session, 1, _Pages([issue], []))
    job = session.scalar(select(Job).where(Job.source_job_id == "1"))

    assert job.status == JobStatus.DISCOVERED
    assert job.last_verified_at is None


def test_failed_poll_rolls_back_jobs_and_records_failure_without_error_text(
    session: Session,
) -> None:
    with pytest.raises(TimeoutError):
        ingest_apibr(session, 1, _Pages([_issue(1)], TimeoutError("private response text")))

    assert session.scalar(select(Job.id)) is None
    run = session.scalar(select(SourceRun))
    source = session.get(JobSource, 1)
    assert run.status == "FAILED"
    assert run.jobs_created == 0
    assert run.errors == "TimeoutError"
    assert "private response text" not in run.errors
    assert source.last_error == "TimeoutError"
