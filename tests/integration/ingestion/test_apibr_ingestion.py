import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.ingestion import apibr as apibr_ingestion
from src.ingestion.apibr import APiBRClient, ingest_apibr, iter_apibr_issues
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
def session(db_session):
    db_session.add(JobSource(id=1, name="APiBR", type="api", polling_mode="INCREMENTAL"))
    db_session.commit()
    return db_session


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


def test_ingest_persists_the_captured_apibr_fixture(session: Session) -> None:
    fixture_path = Path("tests/resources/jobs_fixture.json")
    fixture_issues = json.loads(fixture_path.read_text(encoding="utf-8"))

    result = ingest_apibr(session, 1, _Pages(fixture_issues, []))

    issue = fixture_issues[0]
    job = session.scalar(
        select(Job).where(
            Job.platform == "apibr",
            Job.source_job_id == str(issue["id"]),
        )
    )
    assert result.jobs_found == len(fixture_issues)
    assert result.jobs_created == len(fixture_issues)
    assert job is not None
    assert job.title == issue["title"]
    assert job.job_url == issue["html_url"]
    assert job.status == JobStatus.ACTIVE


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
    assert list(job.embedding) == pytest.approx([0.1, 0.2])

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


def test_state_free_fixture_never_triggers_availability_requests(session, monkeypatch):
    def forbid_network(*_args, **_kwargs):
        raise AssertionError("fixture ingestion must never access the network")

    monkeypatch.setattr(apibr_ingestion, "urlopen", forbid_network)
    issues = json.loads(Path("tests/resources/apibr_issues.json").read_text())
    result = ingest_apibr(session, 1, _Pages(issues, []))
    job = session.scalar(select(Job))
    assert result.jobs_created == len(issues)
    assert job.status == JobStatus.DISCOVERED
    assert job.last_verified_at is None


def test_missing_state_preserves_existing_availability_and_verification(session):
    ingest_apibr(session, 1, _Pages([_issue(1)], []))
    job = session.scalar(select(Job))
    verified_at = job.last_verified_at
    issue = _issue(1)
    issue.pop("state")
    ingest_apibr(session, 1, _Pages([issue], []))
    assert job.status == JobStatus.ACTIVE
    assert job.last_verified_at == verified_at


@pytest.mark.parametrize(
    "bad_record",
    [
        None,
        {"id": 2, "title": ""},
        {"id": 2, "title": "Developer", "created_at": "private-invalid-date"},
        {"id": "x" * 256, "title": "Developer"},
    ],
)
def test_bad_record_does_not_rollback_valid_jobs(session, bad_record):
    result = ingest_apibr(session, 1, _Pages([_issue(1), bad_record, _issue(3)], []))
    run = session.get(SourceRun, result.run_id)
    source = session.get(JobSource, 1)
    assert result.status == run.status == "PARTIAL"
    assert result.jobs_found == 3
    assert result.jobs_created == 2
    assert result.jobs_rejected == run.jobs_rejected == 1
    assert len(session.scalars(select(Job)).all()) == 2
    assert run.errors == source.last_error == "RejectedRecords:1"
    assert source.last_success_at is None
    assert run.snapshot_complete is False
    assert run.jobs_marked_stale == 0


def test_network_failure_rolls_back_availability_changes(session):
    ingest_apibr(session, 1, _Pages([_issue(1)], []))
    with pytest.raises(TimeoutError):
        ingest_apibr(session, 1, _Pages([_issue(1, state="closed")], TimeoutError()))
    assert session.scalar(select(Job)).status == JobStatus.ACTIVE


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
