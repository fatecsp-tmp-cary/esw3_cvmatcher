import json
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from src.ingestion.adapters import SourceError
from src.ingestion.apibr import APiBRAdapter, APiBRClient, ingest_apibr
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun


@pytest.fixture
def source(db_session):
    row = JobSource(name="APiBR adapter tests", type="api", polling_mode="INCREMENTAL")
    db_session.add(row)
    db_session.commit()
    return row


def issue(identity=1, *, title="Python Developer"):
    return {"id": identity, "title": title, "body": "Python APIs", "state": "open"}


def test_retrying_client_remains_compatible_with_partial_ingestion(db_session, source):
    calls = []
    waits = []

    def transport(request, timeout):
        calls.append(request)
        if len(calls) == 1:
            raise URLError("private-upstream-exception")
        page = int(parse_qs(urlsplit(request.full_url).query)["page"][0])
        return json.dumps([issue(), None, issue(2)] if page == 1 else []).encode()

    result = ingest_apibr(
        db_session, source.id, APiBRClient(transport=transport, sleep=waits.append)
    )
    run = db_session.get(SourceRun, result.run_id)
    assert result.status == "PARTIAL"
    assert result.jobs_created == 2
    assert result.jobs_rejected == 1
    assert waits == [1]
    assert result.snapshot_complete is False
    assert run.jobs_absent == 0
    assert run.jobs_marked_stale == 0
    assert run.errors == "RejectedRecords:1"
    assert db_session.get(JobSource, source.id).last_success_at is None
    assert len(db_session.scalars(select(Job)).all()) == 2


def test_exhausted_retry_rolls_back_page_changes_and_preserves_availability(db_session, source):
    original = Job(
        source_id=source.id,
        platform="apibr",
        source_job_id="1",
        title="Original title",
        status=JobStatus.ACTIVE,
    )
    db_session.add(original)
    db_session.commit()
    calls = []
    waits = []

    def transport(request, timeout):
        page = int(parse_qs(urlsplit(request.full_url).query)["page"][0])
        calls.append(page)
        if page == 1:
            return json.dumps([issue(title="Changed title"), issue(2)]).encode()
        raise URLError("private-error-and-url")

    with pytest.raises(SourceError, match="^transport_failure$"):
        ingest_apibr(db_session, source.id, APiBRClient(transport=transport, sleep=waits.append))
    jobs = db_session.scalars(select(Job)).all()
    assert len(jobs) == 1
    assert jobs[0].title == "Original title"
    assert jobs[0].status is JobStatus.ACTIVE
    assert calls == [1, 2, 2, 2]
    assert waits == [1, 2]
    run = db_session.scalar(select(SourceRun))
    assert run.status == "FAILED"
    assert run.errors == "SourceError"
    assert run.snapshot_complete is False
    assert run.jobs_updated == 0
    assert run.jobs_created == 0
    assert db_session.get(JobSource, source.id).last_error == "SourceError"


async def test_async_and_sync_normalization_share_source_identity(db_session, source):
    pages = iter([[issue()], []])
    client = APiBRClient(transport=lambda *_: json.dumps(next(pages)).encode())
    adapter = APiBRAdapter(client)
    raw = [record async for record in adapter.fetch_jobs()]
    expected = adapter.normalize(raw[0])
    pages = iter([raw, []])
    result = ingest_apibr(
        db_session,
        source.id,
        APiBRClient(transport=lambda *_: json.dumps(next(pages)).encode()),
    )
    stored = db_session.scalar(select(Job))
    assert stored.platform == expected["platform"] == adapter.platform
    assert stored.source_job_id == expected["source_job_id"]
    assert stored.title == expected["title"]
    assert result.snapshot_complete is adapter.snapshot_complete is False
