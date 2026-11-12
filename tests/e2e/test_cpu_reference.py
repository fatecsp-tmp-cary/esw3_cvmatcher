"""Opt-in actual offline CPU benchmark, excluded from ordinary CI.

Run only through scripts/testing/postgres.sh -m external on a disposable database.
This measures a homogeneous synthetic 10,000-job load, not ranking quality.
"""

import json
import os
import time
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from src.api.app import CURRICULUM_EXAMPLE, create_app
from src.api.rate_limit import GlobalRateLimiter
from src.embeddings.encoder import LocalEmbeddingEncoder
from src.matching.pipeline import MatchingPipeline
from src.persistence.job.job import Job
from src.persistence.job.job_source import JobSource


@pytest.mark.external
def test_warm_complete_request_cpu_reference(db_engine, monkeypatch):
    if os.environ.get("CVMATCHER_RUN_CPU_REFERENCE") != "1":
        pytest.skip("Explicit opt-in required for actual local model/10k-job benchmark")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    import torch

    torch.set_num_threads(1)
    encoder = LocalEmbeddingEncoder()
    job_text = "Desenvolvedor Python PostgreSQL APIs e serviços de dados"
    vector = encoder.encode_jobs([job_text])[0]
    version = "cpu-reference-synthetic-v1"
    with Session(db_engine) as session, session.begin():
        source = JobSource(name=f"cpu-reference-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.flush()
        source_id = source.id
        session.execute(
            text(
                "INSERT INTO jobs (source_id,platform,source_job_id,title,description,skills,"
                "status,content_hash,embedding) SELECT :source,'benchmark',n::text,:title,"
                ":description,'[\"Python\",\"PostgreSQL\"]'::jsonb,'ACTIVE','benchmark-hash',"
                "CAST(:vector AS vector) FROM generate_series(1,10000) n"
            ),
            {
                "source": source_id,
                "title": job_text,
                "description": job_text,
                "vector": json.dumps(vector),
            },
        )
        session.execute(
            text(
                "INSERT INTO job_extractions (job_id,content_hash,config_version,status,attempts,"
                "updated_at,evidence) SELECT id,content_hash,:version,'SUCCEEDED',1,"
                "clock_timestamp(),'[]'::jsonb FROM jobs WHERE source_id=:source"
            ),
            {"source": source_id, "version": version},
        )
        session.execute(
            text(
                "INSERT INTO job_embeddings (job_id,content_hash,model_version,extraction_version,"
                "status,attempts,updated_at) SELECT id,content_hash,:model,:extraction,"
                "'SUCCEEDED',1,clock_timestamp() FROM jobs WHERE source_id=:source"
            ),
            {"source": source_id, "model": encoder.model_version, "extraction": version},
        )

    def sessions():
        return Session(db_engine)

    body = deepcopy(CURRICULUM_EXAMPLE)
    experience = body["experiencias"][0]
    experience.update(cargo="Desenvolvedor Python", descricao="Python PostgreSQL APIs")
    body["experiencias"] = [deepcopy(experience) for _ in range(10)]
    body["formacoes"] = [deepcopy(body["formacoes"][0]) for _ in range(5)]
    pipeline = MatchingPipeline(sessions, encoder, version)
    durations = []
    try:
        with TestClient(create_app(pipeline, rate_limiter=GlobalRateLimiter(db_engine))) as client:
            for index in range(4):
                started = time.perf_counter()
                response = client.post("/matches?limit=10", json=body)
                elapsed = time.perf_counter() - started
                assert response.status_code == 200
                assert len(response.json()["matches"]) == 10
                if index:
                    durations.append(elapsed)
        report = {
            "jobs": 10000,
            "experiences": 10,
            "education": 5,
            "limit": 10,
            "sequential_requests": 3,
            "torch_cpu_threads": 1,
            "model_version": encoder.model_version,
            "algorithm_version": pipeline.algorithm_version,
            "warm_request_seconds": durations,
            "target_seconds": 5,
            "passed": max(durations) <= 5,
            "limitations": "Homogeneous synthetic jobs and repeated entries; no quality proof.",
        }
        destination = os.environ.get("CVMATCHER_CPU_REPORT")
        if destination:
            Path(destination).write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
        assert report["passed"], "Warm complete-request CPU target exceeded"
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))
