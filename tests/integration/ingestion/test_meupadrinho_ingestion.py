import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import URLError

import pytest
from sqlalchemy import select

from src.ingestion.adapters import SourceError
from src.ingestion.apibr import ingest_apibr
from src.ingestion.meupadrinho import (
    MeuPadrinhoClient,
    ingest_meupadrinho,
    ingest_meupadrinho_jsonl,
    ingest_meupadrinho_records,
)
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun


@pytest.fixture
def source(db_session):
    row = JobSource(name="meupadrinho", type="api", polling_mode="INCREMENTAL")
    db_session.add(row)
    db_session.commit()
    return row


def _record(
    nano_id: str, *, title: str = "Backend Python", closed: bool = False, salario: str = ""
):
    return {
        "nano_id": nano_id,
        "contents": {
            "titulo_vaga": title,
            "local": "São Paulo, SP",
            "horario_registro": "2026-11-10T12:00:00",
            "link_vaga": f"https://linkedin.com/jobs/view/{nano_id}",
            "link_plataforma_publicado": f"https://linkedin.com/jobs/view/{nano_id}",
            "plataforma": "LINKEDIN",
            "forma_trabalho": "remoto",
            "cargo": "BACKEND",
            "nivel": "Senior",
            "descricao_vaga": "Desenvolvimento de APIs Python.",
            "requisitos_tecnicos": "Python; FastAPI; PostgreSQL",
            "requisitos_desejaveis": "Docker; Kubernetes",
            "nivel_vaga": "Sênior",
            "tipo_contrato": "CLT",
            "salario": salario,
            "nome_empresa": "TechCorp",
            "vaga_encerrada": closed,
        },
    }


def test_ingest_meupadrinho_jsonl_creates_updates_and_isolates_rejections(
    db_session, source, tmp_path
):
    jsonl_file = tmp_path / "padrinho_rico.jsonl"
    lines = [
        json.dumps(_record("nano0001", salario="10.000,00 - 14.000,00")),
        "{broken json line",
        json.dumps({"nano_id": "bad", "contents": {"titulo_vaga": ""}}),
        json.dumps(_record("nano0002", closed=True)),
    ]
    jsonl_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = ingest_meupadrinho_jsonl(db_session, source.id, jsonl_file)
    assert result.status == "PARTIAL"
    assert result.jobs_found == 4
    assert result.jobs_created == 2
    assert result.jobs_expired == 1
    assert result.jobs_rejected == 2

    jobs = {
        job.source_job_id: job
        for job in db_session.scalars(select(Job).where(Job.platform == "meupadrinho")).all()
    }
    assert set(jobs.keys()) == {"nano0001", "nano0002"}
    assert jobs["nano0001"].status is JobStatus.ACTIVE
    assert jobs["nano0001"].company == "TechCorp"
    assert jobs["nano0001"].salary == {"min": 10000, "max": 14000}
    assert jobs["nano0001"].currency == "BRL"
    assert jobs["nano0002"].status is JobStatus.EXPIRED


def test_worker_validates_availability_by_oldest_verified_and_expires_closed_or_404(
    db_session, source, tmp_path
):
    jsonl_file = tmp_path / "seed.jsonl"
    jsonl_file.write_text(
        "\n".join(
            [
                json.dumps(_record("job_open")),
                json.dumps(_record("job_closed")),
                json.dumps(_record("job_404")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    ingest_meupadrinho_jsonl(db_session, source.id, jsonl_file)

    now = datetime.now(UTC)
    for idx, jid in enumerate(("job_open", "job_closed", "job_404")):
        row = db_session.scalar(select(Job).where(Job.source_job_id == jid))
        row.last_verified_at = now - timedelta(hours=10 - idx)
    db_session.commit()

    class FakeClient:
        def __init__(self):
            self.checked = []

        def fetch_job(self, nano_id: str):
            self.checked.append(nano_id)
            if nano_id == "job_open":
                return _record("job_open", title="Backend Python Updated")
            if nano_id == "job_closed":
                return _record("job_closed", closed=True)
            if nano_id == "job_404":
                return None
            raise AssertionError(f"unexpected {nano_id}")

    client = FakeClient()
    result = ingest_meupadrinho(db_session, source.id, client, validation_limit=10)

    assert client.checked == ["job_open", "job_closed", "job_404"]
    assert result.status == "SUCCEEDED"
    assert result.jobs_found == 3
    assert result.jobs_updated == 1
    assert result.jobs_unchanged == 2
    assert result.jobs_expired == 2

    jobs = {
        job.source_job_id: job
        for job in db_session.scalars(select(Job).where(Job.platform == "meupadrinho")).all()
    }
    assert jobs["job_open"].status is JobStatus.ACTIVE
    assert jobs["job_open"].title == "Backend Python Updated"
    assert jobs["job_closed"].status is JobStatus.EXPIRED
    assert jobs["job_404"].status is JobStatus.EXPIRED


def test_validation_network_failure_rolls_back_run_changes(db_session, source, tmp_path):
    jsonl_file = tmp_path / "seed.jsonl"
    jsonl_file.write_text(json.dumps(_record("job_1")) + "\n", encoding="utf-8")
    ingest_meupadrinho_jsonl(db_session, source.id, jsonl_file)

    def failing_transport(request, timeout):
        raise URLError("network down")

    with pytest.raises(SourceError, match="^transport_failure$"):
        ingest_meupadrinho(
            db_session,
            source.id,
            MeuPadrinhoClient(transport=failing_transport, sleep=lambda _: None),
        )

    job = db_session.scalar(select(Job).where(Job.source_job_id == "job_1"))
    assert job.status is JobStatus.ACTIVE
    runs = db_session.scalars(
        select(SourceRun).where(SourceRun.source_id == source.id).order_by(SourceRun.id)
    ).all()
    assert runs[-1].status == "FAILED"


def test_meupadrinho_fixture_cross_source_independence_and_terminal_expiration(db_session, source):
    apibr_source = JobSource(name="apibr-coexist", type="api", polling_mode="INCREMENTAL")
    db_session.add(apibr_source)
    db_session.commit()

    class Pages:
        def fetch_page(self, page: int):
            if page == 1:
                return [
                    {
                        "id": "mp910001",
                        "title": "Senior Backend Python Engineer",
                        "body": "Same opportunity on APiBR",
                        "state": "open",
                    }
                ]
            return []

    ingest_apibr(db_session, apibr_source.id, Pages())

    fixture_records = json.loads(
        Path("tests/resources/meupadrinho_vagas.json").read_text(encoding="utf-8")
    )
    result = ingest_meupadrinho_records(db_session, source.id, fixture_records)
    assert result.status == "SUCCEEDED"
    assert result.jobs_created == 3
    assert result.jobs_expired == 1
    assert result.snapshot_complete is False

    # Same source_job_id across apibr and meupadrinho remains independent (no cross-source dedup).
    same_id_jobs = db_session.scalars(
        select(Job).where(Job.source_job_id == "mp910001").order_by(Job.platform)
    ).all()
    assert [(j.platform, j.status) for j in same_id_jobs] == [
        ("apibr", JobStatus.ACTIVE),
        ("meupadrinho", JobStatus.ACTIVE),
    ]

    # Terminal EXPIRED cannot be reopened if source later reports vaga_encerrada=False.
    reopened_payload = dict(fixture_records[2])
    reopened_payload["contents"] = {**reopened_payload["contents"], "vaga_encerrada": False}
    reopen_res = ingest_meupadrinho_records(db_session, source.id, [reopened_payload])
    assert reopen_res.jobs_reactivated == 0
    expired_job = db_session.scalar(
        select(Job).where(Job.platform == "meupadrinho", Job.source_job_id == "mp910003")
    )
    assert expired_job.status is JobStatus.EXPIRED


def test_ingest_meupadrinho_live_discovery_and_stale_reactivation(db_session, source):
    # Seed a STALE job that will be re-verified as open, plus discover a brand-new job.
    ingest_meupadrinho_records(db_session, source.id, [_record("stale_job")])
    stale_row = db_session.scalar(
        select(Job).where(Job.platform == "meupadrinho", Job.source_job_id == "stale_job")
    )
    stale_row.status = JobStatus.STALE
    db_session.commit()

    class DiscoveryClient:
        def fetch_listing(self, params=None):
            return [{"nano_id": "stale_job"}, {"nano_id": "discovered_job"}, {"bad": "record"}]

        def fetch_job(self, nano_id: str):
            return _record(nano_id, title=f"Title for {nano_id}")

    result = ingest_meupadrinho(
        db_session,
        source.id,
        DiscoveryClient(),
        validation_limit=10,
        discover_new=True,
        listing_queries=({"cargos": "backend"},),
    )
    assert result.status == "PARTIAL"
    assert result.jobs_created == 1
    assert result.jobs_reactivated == 1
    assert result.jobs_rejected == 1

    refreshed_stale = db_session.scalar(
        select(Job).where(Job.platform == "meupadrinho", Job.source_job_id == "stale_job")
    )
    discovered = db_session.scalar(
        select(Job).where(Job.platform == "meupadrinho", Job.source_job_id == "discovered_job")
    )
    assert refreshed_stale.status is JobStatus.ACTIVE
    assert discovered is not None and discovered.status is JobStatus.ACTIVE
