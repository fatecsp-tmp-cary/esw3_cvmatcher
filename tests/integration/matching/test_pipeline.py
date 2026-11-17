"""Synthetic PostgreSQL-to-production-API regressions with deterministic inference."""

from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session

from src.api.app import CURRICULUM_EXAMPLE, create_app
from src.api.rate_limit import GlobalRateLimiter
from src.embeddings.config import EmbeddingConfig
from src.embeddings.service import EmbeddingWorker
from src.embeddings.service import enqueue as enqueue_embedding
from src.extraction.contracts import SpanEvidence
from src.extraction.service import ExtractionWorker, enqueue
from src.matching.pipeline import MatchingPipeline
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource

VERSION = "pipeline-test-extraction-v1"
VECTOR = [1.0] + [0.0] * 383


class Encoder:
    config = EmbeddingConfig()
    model_version = config.model_version

    def __init__(self):
        self.calls = []

    def encode_jobs(self, texts):
        return [VECTOR for _ in texts]

    def encode_queries(self, texts):
        self.calls.append(list(texts))
        return [VECTOR for _ in texts]


class Extractor:
    def extract(self, text):
        start = text.index("Python")
        return [SpanEvidence(start, start + 6, "skill", 0.9)]


@pytest.fixture
def populated(db_engine):
    identities = []
    with Session(db_engine) as session, session.begin():
        source = JobSource(name=f"pipeline-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.flush()
        source_id = source.id
        for platform, status in (
            ("a-independent", JobStatus.ACTIVE),
            ("b-independent", JobStatus.ACTIVE),
            ("c-withheld", JobStatus.ACTIVE),
            ("d-expired", JobStatus.EXPIRED),
        ):
            job = Job(
                source_id=source_id,
                platform=platform,
                source_job_id="same-upstream-id",
                title="Python Developer",
                description="Desenvolvimento Python e PostgreSQL",
                skills=["Python", "PostgreSQL"],
                location={"city": "Lisboa", "country": "PT"},
                content_hash="synthetic-content-v1",
                status=status,
            )
            session.add(job)
            session.flush()
            identities.append(job.id)
            if platform in ("a-independent", "b-independent"):
                enqueue(session, job.id, VERSION)
    encoder = Encoder()

    def sessions():
        return Session(db_engine)

    extractor = ExtractionWorker(sessions, Extractor(), VERSION)
    assert extractor.process_once()
    assert extractor.process_once()
    with Session(db_engine) as session, session.begin():
        for identifier in identities[:2]:
            enqueue_embedding(session, identifier, encoder.config, VERSION)
    embedder = EmbeddingWorker(sessions, encoder, VERSION)
    assert embedder.process_once()
    assert embedder.process_once()
    try:
        yield sessions, encoder, identities
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))


def curriculum():
    body = deepcopy(CURRICULUM_EXAMPLE)
    body["experiencias"][0]["cargo"] = "Python Developer"
    body["experiencias"][0]["descricao"] = "Python PostgreSQL"
    body["competencias"] = [{"descricao": "Python", "nivel": "avançado"}]
    return body


def test_background_to_api_ranking_is_repeatable_private_and_source_independent(
    db_engine, populated, caplog
):
    sessions, encoder, identities = populated
    pipeline = MatchingPipeline(sessions, encoder, VERSION)
    body = curriculum()
    with TestClient(create_app(pipeline, rate_limiter=GlobalRateLimiter(db_engine))) as client:
        first = client.post("/matches", json=body)
        second = client.post("/matches", json=body)
        limited = client.post("/matches?limit=1", json=body)
    assert first.status_code == 200
    assert first.json() == second.json()
    matches = first.json()["matches"]
    assert [match["job"]["id"] for match in matches] == identities[:2]
    assert len(limited.json()["matches"]) == 1
    assert all(match["eligibility"] for match in matches)
    assert all(0 <= match["score"] <= 100 for match in matches)
    assert all(match["matched_skills"] == ["postgresql", "python"] for match in matches)
    assert all(match["missing_requirements"] == [] for match in matches)
    assert all(match["embedding_model"] == encoder.model_version for match in matches)
    # Identical jobs from two platforms stay separate, including foreign location.
    assert matches[0]["job"]["location"]["country"] == "PT"
    assert body["curriculo_id"] not in first.text + caplog.text
    assert body["experiencias"][0]["descricao"] not in caplog.text
    assert all("candidate" not in name for name in inspect(db_engine).get_table_names())
    assert len(encoder.calls[0]) == len(body["experiencias"]) + len(body["formacoes"])


def test_empty_sections_do_not_invent_evidence_or_run_inference(populated):
    from src.schemas.candidate.curriculum import CurriculumRequest

    sessions, encoder, _ = populated
    body = {key: [] for key in ("experiencias", "formacoes", "competencias", "projetos", "idiomas")}
    body["curriculo_id"] = str(uuid4())
    assert (
        MatchingPipeline(sessions, encoder, VERSION)(
            CurriculumRequest.model_validate(body), 10
        ).matches
        == []
    )
    assert encoder.calls == []


def test_content_or_extraction_version_change_withholds_every_path(populated):
    from src.schemas.candidate.curriculum import CurriculumRequest

    sessions, encoder, identities = populated
    with sessions() as session, session.begin():
        for identifier in identities[:2]:
            session.get(Job, identifier).content_hash = "changed-content"
    request = CurriculumRequest.model_validate(curriculum())
    assert MatchingPipeline(sessions, encoder, VERSION)(request, 10).matches == []
    assert MatchingPipeline(sessions, encoder, "new-version")(request, 10).matches == []


def test_inference_failure_is_privacy_safe_and_does_not_mutate_job_data(populated, monkeypatch):
    from src.api import runtime

    sessions, encoder, identities = populated

    def broken(_texts):
        raise RuntimeError("private candidate text and secret dependency detail")

    encoder.encode_queries = broken
    monkeypatch.setattr(
        runtime, "get_pipeline", lambda: MatchingPipeline(sessions, encoder, VERSION)
    )
    with TestClient(create_app(runtime.production_matches)) as client:
        response = client.post("/matches", json=curriculum())
    assert response.status_code == 500
    assert "private candidate" not in response.text
    assert "secret" not in response.text
    with sessions() as session:
        assert (
            session.scalars(select(Job.id).where(Job.id.in_(identities)).order_by(Job.id)).all()
            == identities
        )


GROUPED = (
    ("a-active", JobStatus.ACTIVE),
    ("b-stale", JobStatus.STALE),
    ("c-expired", JobStatus.EXPIRED),
    ("d-discovered", JobStatus.DISCOVERED),
    ("e-active", JobStatus.ACTIVE),
)


@pytest.fixture
def grouped(db_engine):
    """Identical ready jobs processed while active, then moved to their final status.

    One additional inactive job is never extracted, so it must stay withheld.
    """
    identities = {}
    with Session(db_engine) as session, session.begin():
        source = JobSource(name=f"grouped-{uuid4()}", type="api", polling_mode="SNAPSHOT")
        session.add(source)
        session.flush()
        source_id = source.id
        for platform in [name for name, _ in GROUPED] + ["f-withheld"]:
            job = Job(
                source_id=source_id,
                platform=platform,
                source_job_id="same-upstream-id",
                title="Python Developer",
                description="Desenvolvimento Python e PostgreSQL",
                skills=["Python", "PostgreSQL"],
                content_hash="synthetic-content-v1",
                status=JobStatus.ACTIVE,
            )
            session.add(job)
            session.flush()
            identities[platform] = job.id
            if platform != "f-withheld":
                enqueue(session, job.id, VERSION)
    encoder = Encoder()

    def sessions():
        return Session(db_engine)

    extractor = ExtractionWorker(sessions, Extractor(), VERSION)
    for _ in GROUPED:
        assert extractor.process_once()
    with Session(db_engine) as session, session.begin():
        for platform, _ in GROUPED:
            enqueue_embedding(session, identities[platform], encoder.config, VERSION)
    embedder = EmbeddingWorker(sessions, encoder, VERSION)
    for _ in GROUPED:
        assert embedder.process_once()
    with Session(db_engine) as session, session.begin():
        for platform, status in (*GROUPED, ("f-withheld", JobStatus.STALE)):
            session.get(Job, identities[platform]).status = status
    try:
        yield sessions, encoder, identities
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))


def test_inactive_jobs_complete_the_ranking_only_after_every_active_job(db_engine, grouped):
    sessions, encoder, identities = grouped
    pipeline = MatchingPipeline(sessions, encoder, VERSION)
    body = curriculum()
    with TestClient(create_app(pipeline, rate_limiter=GlobalRateLimiter(db_engine))) as client:
        first = client.post("/matches", json=body).json()["matches"]
        second = client.post("/matches", json=body).json()["matches"]
        two = client.post("/matches?limit=2", json=body).json()["matches"]
        three = client.post("/matches?limit=3", json=body).json()["matches"]

    assert first == second
    order = ["a-active", "e-active", "b-stale", "c-expired", "d-discovered"]
    assert [match["job"]["id"] for match in first] == [identities[name] for name in order]
    assert [match["eligibility"] for match in first] == [True, True, False, False, False]
    assert [match["rank"] for match in first] == [1, 2, 3, 4, 5]
    # Status decides the group only: identical jobs keep one compatibility score.
    assert len({match["score"] for match in first}) == 1
    assert all(match["matched_skills"] == ["postgresql", "python"] for match in first)
    # Extraction readiness still gates the inactive group.
    assert identities["f-withheld"] not in {match["job"]["id"] for match in first}

    # Enough active jobs fill the limit: no inactive job is returned.
    assert [match["job"]["id"] for match in two] == [identities[name] for name in order[:2]]
    assert all(match["eligibility"] for match in two)
    # The inactive group fills only the remaining positions.
    assert [match["job"]["id"] for match in three] == [identities[name] for name in order[:3]]
    assert [match["eligibility"] for match in three] == [True, True, False]


def test_only_inactive_ready_jobs_are_returned_as_ineligible(db_engine, grouped):
    sessions, encoder, identities = grouped
    with Session(db_engine) as session, session.begin():
        for name in ("a-active", "e-active"):
            session.get(Job, identities[name]).status = JobStatus.STALE
    pipeline = MatchingPipeline(sessions, encoder, VERSION)
    with TestClient(create_app(pipeline, rate_limiter=GlobalRateLimiter(db_engine))) as client:
        matches = client.post("/matches", json=curriculum()).json()["matches"]

    assert len(matches) == 5
    assert not any(match["eligibility"] for match in matches)
    assert [match["rank"] for match in matches] == [1, 2, 3, 4, 5]


@pytest.fixture
def enriched(db_engine):
    """One ready job whose stored skills lack a skill the worker associates."""
    with Session(db_engine) as session, session.begin():
        source = JobSource(name=f"enriched-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.flush()
        source_id = source.id
        job = Job(
            source_id=source_id,
            platform="a-enriched",
            source_job_id="1",
            title="Backend Developer",
            description="Requisitos: Python",
            skills=["PostgreSQL"],
            content_hash="synthetic-content-v1",
            status=JobStatus.ACTIVE,
        )
        session.add(job)
        session.flush()
        job_id = job.id
        enqueue(session, job_id, VERSION)
    encoder = Encoder()

    def sessions():
        return Session(db_engine)

    assert ExtractionWorker(sessions, Extractor(), VERSION).process_once()
    with Session(db_engine) as session, session.begin():
        enqueue_embedding(session, job_id, encoder.config, VERSION)
    assert EmbeddingWorker(sessions, encoder, VERSION).process_once()
    try:
        yield sessions, encoder, job_id
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))


def test_result_skills_combine_stored_and_extracted_skills_without_changing_the_job(
    db_engine, enriched
):
    sessions, encoder, job_id = enriched
    pipeline = MatchingPipeline(sessions, encoder, VERSION)
    with TestClient(create_app(pipeline, rate_limiter=GlobalRateLimiter(db_engine))) as client:
        matches = client.post("/matches", json=curriculum()).json()["matches"]

    assert [match["job"]["id"] for match in matches] == [job_id]
    assert matches[0]["job"]["skills"] == ["PostgreSQL", "Python"]
    with Session(db_engine) as session:
        assert session.get(Job, job_id).skills == ["PostgreSQL"]


def test_typo_support_on_both_sides_keeps_exclusions_disabled_and_candidate_private(
    populated, caplog
):
    from src.extraction.persistence import persist_requirements
    from src.schemas.candidate.curriculum import CurriculumRequest

    sessions, encoder, identities = populated
    with sessions() as session, session.begin():
        for identifier in identities[:2]:
            job = session.get(Job, identifier)
            job.skills = []
            job.description = "Pyhton required."
            text = job.title + "\n" + job.description
            start = text.rindex("Pyhton")
            rows = [SpanEvidence(start, start + 6, "skill", 0.9).serialize(text)]
            persist_requirements(session, job, rows, text)
            assert rows[0]["approximate_match"] and not rows[0]["exclusion_safe"]
    body = curriculum()
    for entry in body["experiencias"]:
        entry["cargo"] = "Pythom Developer"
        entry["descricao"] = "Pythom PostgreSQL"
    body["competencias"] = [{"descricao": "Pythom", "nivel": "avançado"}]
    result = MatchingPipeline(sessions, encoder, VERSION)(
        CurriculumRequest.model_validate(body), 10
    )
    assert len(result.matches) == 2
    assert all("python" in row.matched_skills for row in result.matches)
    assert all(row.eligibility and row.missing_requirements == [] for row in result.matches)
    assert "Pythom" not in caplog.text and body["curriculo_id"] not in caplog.text


@pytest.mark.parametrize(
    "override",
    [
        {"approximate_match": True},
        {"negated": True},
        {"conflicting": True},
        {"requirement_class": None},
        {"canonical_skill": None},
    ],
)
def test_untrusted_extracted_skills_stay_score_only(enriched, override):
    from src.persistence.extraction import JobExtraction
    from src.schemas.candidate.curriculum import CurriculumRequest

    sessions, encoder, job_id = enriched
    with sessions() as session, session.begin():
        state = session.get(JobExtraction, job_id)
        state.evidence = [{**row, **override} for row in state.evidence]
        job = session.get(Job, job_id)
        before = job.skills[:], job.content_hash
    result = MatchingPipeline(sessions, encoder, VERSION)(
        CurriculumRequest.model_validate(curriculum()), 10
    )
    (match,) = result.matches
    assert match.job.skills == ["PostgreSQL"]
    # The existing association remains score support and is not deleted or hidden.
    assert "python" in match.matched_skills
    with sessions() as session:
        job = session.get(Job, job_id)
        assert (job.skills, job.content_hash) == before


def test_missing_retained_provenance_does_not_authorize_display(enriched):
    from src.persistence.extraction import JobExtraction
    from src.schemas.candidate.curriculum import CurriculumRequest

    sessions, encoder, job_id = enriched
    with sessions() as session, session.begin():
        session.get(JobExtraction, job_id).evidence = None
    result = MatchingPipeline(sessions, encoder, VERSION)(
        CurriculumRequest.model_validate(curriculum()), 10
    )
    (match,) = result.matches
    assert match.job.skills == ["PostgreSQL"]
    assert "python" in match.matched_skills


@pytest.mark.parametrize("path", ["textual", "semantic"])
def test_status_change_cannot_repeat_a_job_or_consume_the_next_group_limit(
    grouped, monkeypatch, path
):
    from src.matching import pipeline as module
    from src.matching.ranking import RankingPolicy
    from src.persistence.job.job import INACTIVE_STATUSES
    from src.schemas.candidate.curriculum import CurriculumRequest

    sessions, encoder, identities = grouped
    target = identities["a-active"]
    retrieve = module.retrieve_textual
    changed = False

    def transition(session, candidate, **kwargs):
        nonlocal changed
        if kwargs["statuses"] == INACTIVE_STATUSES and not changed:
            # Independent committed writer between the active and inactive passes.
            with sessions() as writer, writer.begin():
                writer.get(Job, target).status = JobStatus.STALE
            changed = True
        return retrieve(session, candidate, **kwargs)

    monkeypatch.setattr(module, "retrieve_textual", transition)
    body = curriculum()
    body["formacoes"] = body["projetos"] = body["idiomas"] = []
    if path == "textual":
        body["experiencias"] = []
    else:
        body["competencias"] = []
        body["experiencias"][0]["cargo"] = "Unrelated vocabulary"
        body["experiencias"][0]["descricao"] = "Distinct words"
    response = MatchingPipeline(
        sessions, encoder, VERSION, ranking=RankingPolicy(retrieval_limit=1)
    )(CurriculumRequest.model_validate(body), 2)
    assert changed
    assert [row.job.id for row in response.matches] == [target, identities["b-stale"]]
    assert [row.eligibility for row in response.matches] == [True, False]
    assert [row.rank for row in response.matches] == [1, 2]


def test_long_description_boilerplate_does_not_reduce_semantic_score_when_core_matches(
    populated,
):
    from src.persistence.embedding import JobEmbedding
    from src.schemas.candidate.curriculum import CurriculumRequest

    sessions, encoder, identities = populated
    orthogonal = [0.0, 1.0] + [0.0] * 382
    with sessions() as session, session.begin():
        # Job 0 has its full embedding diluted by boilerplate (orthogonal to VECTOR),
        # while its core_embedding matches VECTOR. Job 1 has both orthogonal.
        session.get(Job, identities[0]).embedding = orthogonal
        session.get(JobEmbedding, identities[0]).core_embedding = VECTOR
        session.get(Job, identities[1]).embedding = orthogonal
        session.get(JobEmbedding, identities[1]).core_embedding = orthogonal
    response = MatchingPipeline(sessions, encoder, VERSION)(
        CurriculumRequest.model_validate(curriculum()), 10
    )
    assert [row.job.id for row in response.matches] == identities[:2]
    assert response.matches[0].score > response.matches[1].score


def test_tiered_bidirectional_skill_scoring_favors_rich_meupadrinho_over_sparse_apibr(db_engine):
    from datetime import UTC, datetime

    from src.persistence.embedding import JobEmbedding
    from src.persistence.extraction import JobExtraction
    from src.persistence.job.skill import JobRequirement, RequirementClass, Skill
    from src.schemas.candidate.curriculum import CurriculumRequest

    with Session(db_engine) as session, session.begin():
        source = JobSource(name=f"tiered-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.flush()
        source_id = source.id
        apibr = Job(
            source_id=source_id,
            platform="apibr",
            source_job_id="sparse-1",
            title="Python Developer",
            description="Vaga backend",
            skills=["Python"],
            content_hash="h1",
            status=JobStatus.ACTIVE,
            embedding=VECTOR,
        )
        meupadrinho = Job(
            source_id=source_id,
            platform="meupadrinho",
            source_job_id="rich-1",
            title="Python Developer",
            description="Vaga backend",
            skills=["Python", "PostgreSQL", "Docker", "FastAPI"],
            content_hash="h2",
            status=JobStatus.ACTIVE,
            embedding=VECTOR,
        )
        session.add_all([apibr, meupadrinho])
        session.flush()
        now = datetime.now(UTC)
        for job in (apibr, meupadrinho):
            session.add_all(
                [
                    JobExtraction(
                        job_id=job.id,
                        content_hash=job.content_hash,
                        config_version=VERSION,
                        status="SUCCEEDED",
                        attempts=1,
                        evidence=[],
                        updated_at=now,
                    ),
                    JobEmbedding(
                        job_id=job.id,
                        content_hash=job.content_hash,
                        model_version=EmbeddingConfig().model_version,
                        extraction_version=VERSION,
                        status="SUCCEEDED",
                        attempts=1,
                        updated_at=now,
                        core_embedding=VECTOR,
                    ),
                ]
            )
        # Add optional skills on meupadrinho that the candidate lacks.
        extra_skill = session.scalar(select(Skill).where(Skill.canonical_name == "Kubernetes"))
        if extra_skill is None:
            extra_skill = Skill(canonical_name="Kubernetes", aliases=["kubernetes"])
            session.add(extra_skill)
            session.flush()
        session.add(
            JobRequirement(
                job_id=meupadrinho.id,
                text="Kubernetes",
                requirement_class=RequirementClass.NICE_TO_HAVE,
                skill_id=extra_skill.id,
            )
        )
        apibr_id, meupadrinho_id = apibr.id, meupadrinho.id
    body = curriculum()
    body["experiencias"][0]["descricao"] = "Python PostgreSQL Docker FastAPI AWS Redis"
    body["competencias"] = [
        {"descricao": name, "nivel": "avancado"}
        for name in ("Python", "PostgreSQL", "Docker", "FastAPI", "AWS", "Redis")
    ]
    try:
        response = MatchingPipeline(lambda: Session(db_engine), Encoder(), VERSION)(
            CurriculumRequest.model_validate(body), 10
        )
        assert [row.job.id for row in response.matches] == [meupadrinho_id, apibr_id]
        assert response.matches[0].score > response.matches[1].score
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))


def test_non_core_education_and_old_experience_skills_cannot_inflate_precision(db_engine):
    from datetime import UTC, datetime

    from src.persistence.embedding import JobEmbedding
    from src.persistence.extraction import JobExtraction
    from src.schemas.candidate.curriculum import CurriculumRequest

    with Session(db_engine) as session, session.begin():
        source = JobSource(name=f"noncore-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.flush()
        source_id = source.id
        job = Job(
            source_id=source_id,
            platform="meupadrinho",
            source_job_id="five-skills",
            title="Platform Engineer",
            description="Python SQL Java Kafka Docker Kubernetes",
            skills=["Python", "SQL", "Java", "Kafka", "Docker"],
            content_hash="h-noncore",
            status=JobStatus.ACTIVE,
            embedding=VECTOR,
        )
        session.add(job)
        session.flush()
        job_id = job.id
        now = datetime.now(UTC)
        session.add_all(
            [
                JobExtraction(
                    job_id=job_id,
                    content_hash=job.content_hash,
                    config_version=VERSION,
                    status="SUCCEEDED",
                    attempts=1,
                    evidence=[],
                    updated_at=now,
                ),
                JobEmbedding(
                    job_id=job_id,
                    content_hash=job.content_hash,
                    model_version=EmbeddingConfig().model_version,
                    extraction_version=VERSION,
                    status="SUCCEEDED",
                    attempts=1,
                    updated_at=now,
                    core_embedding=VECTOR,
                ),
            ]
        )

    body = curriculum()
    body["projetos"] = []
    body["idiomas"] = []
    body["experiencias"] = [
        {
            "empresa": f"Co {i}",
            "cargo": "Python Developer" if i < 3 else "Java Kafka Engineer",
            "descricao": "Python SQL" if i < 3 else "Java Kafka",
            "inicio": f"202{3 - i}-01-01",
            "fim": f"202{3 - i}-12-01",
        }
        for i in range(4)
    ]
    body["formacoes"] = [
        {
            "instituicao": "Univ",
            "curso": "Docker e Kubernetes",
            "nivel": "especializacao",
            "status": "concluido",
            "inicio": "2022-01-01",
            "fim": "2022-12-01",
        }
    ]
    body["competencias"] = [
        {"descricao": "Python", "nivel": "avancado"},
        {"descricao": "SQL", "nivel": "avancado"},
    ]
    try:
        response = MatchingPipeline(lambda: Session(db_engine), Encoder(), VERSION)(
            CurriculumRequest.model_validate(body), 10
        )
        (match,) = response.matches
        assert match.job.id == job_id
        # Only core-supported skills (Python, SQL) count; old Java/Kafka and course Docker do not.
        assert match.matched_skills == ["python", "sql"]
        # Compare against a candidate with all 5 skills in core: non-core skills stay excluded.
        full_body = deepcopy(body)
        full_body["competencias"].extend(
            {"descricao": name, "nivel": "avancado"} for name in ("Java", "Kafka", "Docker")
        )
        (full_match,) = MatchingPipeline(lambda: Session(db_engine), Encoder(), VERSION)(
            CurriculumRequest.model_validate(full_body), 10
        ).matches
        assert match.score < full_match.score
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))
