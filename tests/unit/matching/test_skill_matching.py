"""Regressions for request-scoped skill matching latency and label-only matching."""

import sys
import time
from types import SimpleNamespace

from src.embeddings.config import EmbeddingConfig
from src.matching.pipeline import MatchingPipeline
from src.persistence.job.job import JobStatus
from src.schemas.candidate.curriculum import CurriculumRequest


class _ScalarsResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)

    def __iter__(self):
        return iter(self._items)


class _FakeSession:
    def __init__(self, jobs):
        self._jobs = jobs
        self._step = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def _is_inactive(self, statement) -> bool:
        params = statement.compile().params.values()
        return any(
            (
                isinstance(v, (list, tuple, set))
                and any(getattr(item, "value", item) == "STALE" for item in v)
            )
            or (
                not isinstance(v, (list, tuple, set, dict))
                and getattr(v, "value", v) in {"STALE", "EXPIRED", "DISCOVERED"}
            )
            for v in params
        )

    def execute(self, statement):
        text = str(statement)
        if "FROM job " in text or "FROM jobs " in text:
            if self._is_inactive(statement):
                return []
            # retrieve_textual and recomputed text_scores
            return [(job, 1.0) for job in self._jobs]
        if "FROM job_extraction" in text or "FROM job_extractions" in text:
            return []
        if "FROM job_skill" in text or "FROM job_skills" in text:
            return []
        if "FROM job_requirement" in text or "FROM job_requirements" in text:
            return []
        return []

    def scalars(self, statement):
        if self._is_inactive(statement):
            return _ScalarsResult([])
        first_line = str(statement).splitlines()[0].strip()
        if first_line == "SELECT jobs.id":
            return _ScalarsResult([job.id for job in self._jobs])
        return _ScalarsResult(self._jobs)


def _job(job_id: int, *, skills: list[str], title: str = "Backend Developer"):
    return SimpleNamespace(
        id=job_id,
        platform="fixture",
        source_job_id=str(job_id),
        title=title,
        company="Acme",
        description=f"Vaga {job_id}",
        keywords=[],
        location=None,
        work_arrangement=None,
        seniority_level=None,
        salary=None,
        currency=None,
        job_url=f"https://example.com/jobs/{job_id}",
        publication_date=None,
        skills=skills,
        status=JobStatus.ACTIVE,
        embedding=None,
    )


def _fake_pipeline(jobs, monkeypatch):
    monkeypatch.setitem(
        sys.modules, "numpy", SimpleNamespace(asarray=lambda v, dtype=None: v, float64=float)
    )
    monkeypatch.setitem(
        sys.modules,
        "src.embeddings.encoder",
        SimpleNamespace(normalized_vector=lambda v: v),
    )
    encoder = SimpleNamespace(
        config=EmbeddingConfig(),
        model_version="e5-small-v1",
        encode_queries=lambda texts: [],
    )
    return MatchingPipeline(lambda: _FakeSession(jobs), encoder, "ext-v1")


def test_label_only_competencies_and_rest_prose_match_job_skills_and_score(monkeypatch):
    jobs = [
        _job(1, skills=["Spring", "REST"]),
        _job(2, skills=["Go", "Terraform"]),
    ]
    pipeline = _fake_pipeline(jobs, monkeypatch)
    request = CurriculumRequest.model_validate(
        {
            "curriculo_id": "11111111-1111-4111-8111-111111111111",
            "formacoes": [],
            "experiencias": [],
            "projetos": [],
            "competencias": [
                {"descricao": "Spring", "nivel": "avancado"},
                {"descricao": "Desenvolvimento de APIs REST", "nivel": "intermediario"},
            ],
            "idiomas": [],
        }
    )

    response = pipeline(request, limit=10)
    assert [match.job.id for match in response.matches] == [1, 2]
    assert response.matches[0].matched_skills == ["rest", "spring framework"]
    assert response.matches[0].score > response.matches[1].score


def test_matching_pool_with_unknown_job_skills_stays_fast_for_long_cv(monkeypatch):
    filler = " ".join(f"palavra{i}" for i in range(420))
    jobs = [
        _job(
            i,
            skills=["Python", "PostgreSQL", "Spring", f"UnknownInternalSkill{i}"],
        )
        for i in range(1, 201)
    ]
    pipeline = _fake_pipeline(jobs, monkeypatch)
    request = CurriculumRequest.model_validate(
        {
            "curriculo_id": "22222222-2222-4222-8222-222222222222",
            "formacoes": [],
            "experiencias": [],
            "projetos": [],
            "competencias": [
                {"descricao": "Python", "nivel": "avancado"},
                {"descricao": "Spring", "nivel": "intermediario"},
                {"descricao": f"Experiência em {filler} com PostgreSQL", "nivel": "avancado"},
            ],
            "idiomas": [],
        }
    )

    started = time.perf_counter()
    response = pipeline(request, limit=200)
    elapsed = time.perf_counter() - started

    assert len(response.matches) == 200
    assert response.matches[0].matched_skills == ["postgresql", "python", "spring framework"]
    assert elapsed < 1.0
