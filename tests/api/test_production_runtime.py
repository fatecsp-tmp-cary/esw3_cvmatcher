"""Exercise the module application's production executor and readiness boundary."""

from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import ArgumentError, InterfaceError, OperationalError

from src.api import runtime
from src.api.app import CURRICULUM_EXAMPLE, app
from src.api.errors import DependencyUnavailableError
from src.api.rate_limit import GlobalRateLimiter
from src.embeddings.encoder import EmbeddingUnavailableError
from src.schemas.candidate.curriculum import CurriculumRequest
from src.schemas.matches import MatchedJob, MatchesResponse, MatchResult

PRIVATE = "private-candidate-or-library-message"


@pytest.fixture
def production_client(monkeypatch):
    # Admission has its own independent PostgreSQL boundary/concurrency tests.
    monkeypatch.setattr(GlobalRateLimiter, "allow", lambda self: True)
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("has_match", [True, False])
def test_module_production_executor_passes_request_and_limit(
    monkeypatch, production_client, has_match
):
    received = []
    matches = (
        [
            MatchResult(
                rank=1,
                job=MatchedJob(id=1, title="Python developer"),
                score=80,
                eligibility=True,
                matched_skills=["Python"],
                missing_requirements=[],
                embedding_model="test-model",
                algorithm_version="test-algorithm",
            )
        ]
        if has_match
        else []
    )

    def pipeline(request, limit):
        received.append((request, limit))
        return MatchesResponse(matches=matches)

    monkeypatch.setattr(runtime, "get_pipeline", lambda: pipeline)
    response = production_client.post("/matches?limit=7", json=CURRICULUM_EXAMPLE)
    assert response.status_code == 200
    assert response.json() == MatchesResponse(matches=matches).model_dump(mode="json")
    request, limit = received[0]
    assert isinstance(request, CurriculumRequest) and limit == 7
    assert request.experiencias[0].cargo == CURRICULUM_EXAMPLE["experiencias"][0]["cargo"]
    assert "curriculo_id" not in response.text


@pytest.mark.parametrize(
    "error",
    [
        OperationalError(None, None, Exception(PRIVATE)),
        InterfaceError(None, None, Exception(PRIVATE)),
        EmbeddingUnavailableError(PRIVATE),
    ],
)
def test_known_dependency_failure_returns_private_503(
    monkeypatch, production_client, caplog, error
):
    def pipeline(request, limit):
        raise error

    monkeypatch.setattr(runtime, "get_pipeline", lambda: pipeline)
    response = production_client.post("/matches", json=CURRICULUM_EXAMPLE)
    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert PRIVATE not in response.text + caplog.text
    assert str(CURRICULUM_EXAMPLE["curriculo_id"]) not in response.text + caplog.text


@pytest.mark.parametrize("error", [ValueError(PRIVATE), RuntimeError(PRIVATE)])
def test_unexpected_pipeline_failure_uses_500_and_safe_source_diagnostics(
    monkeypatch, production_client, caplog, error
):
    def broken_pipeline(request, limit):
        raise error

    monkeypatch.setattr(runtime, "get_pipeline", lambda: broken_pipeline)
    response = production_client.post("/matches", json=CURRICULUM_EXAMPLE)
    assert response.status_code == 500
    assert "Unhandled " + type(error).__name__ in caplog.text
    assert "broken_pipeline" in caplog.text
    assert PRIVATE not in response.text + caplog.text
    assert str(CURRICULUM_EXAMPLE["curriculo_id"]) not in response.text + caplog.text


@pytest.mark.parametrize("failure", [None, "database", "model", "programming"])
def test_module_readiness_checks_database_and_model(
    monkeypatch, production_client, caplog, failure
):
    calls = []

    class Session:
        def execute(self, statement):
            calls.append("database")
            assert "job_extractions" in str(statement)
            if failure == "database":
                raise OperationalError(None, None, Exception(PRIVATE))
            return SimpleNamespace(all=lambda: [])

    @contextmanager
    def sessions():
        yield Session()

    def encode(texts):
        calls.append("model")
        assert texts == ["model readiness"]
        if failure == "model":
            raise EmbeddingUnavailableError(PRIVATE)
        if failure == "programming":
            raise ValueError(PRIVATE)
        return [[1.0]]

    pipeline = SimpleNamespace(sessions=sessions, encoder=SimpleNamespace(encode_queries=encode))
    monkeypatch.setattr(runtime, "get_pipeline", lambda: pipeline)
    response = production_client.get("/health")
    assert response.status_code == (
        200 if failure is None else 500 if failure == "programming" else 503
    )
    assert calls == (["database"] if failure == "database" else ["database", "model"])
    assert PRIVATE not in response.text + caplog.text


@pytest.fixture
def empty_pipeline_cache():
    runtime._configured_pipeline.cache_clear()
    yield
    runtime._configured_pipeline.cache_clear()


def test_configured_factory_composes_and_reuses_pipeline(monkeypatch, empty_pipeline_cache):
    from src.embeddings import encoder
    from src.extraction.gliner import EXTRACTION_VERSION
    from src.matching import pipeline
    from src.persistence import database

    engine, sessions, model, configured = object(), object(), object(), object()
    calls = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://synthetic/runtime_test")
    monkeypatch.setenv("CVMATCHER_EMBEDDING_CACHE", "/synthetic/cache")
    monkeypatch.setattr(database, "create_db_engine", lambda: engine)

    def create_sessions(value):
        assert value is engine
        return sessions

    def create_encoder(config):
        assert config.cache_directory == "/synthetic/cache"
        return model

    def create_pipeline(*args):
        calls.append(args)
        return configured

    monkeypatch.setattr(database, "create_session_factory", create_sessions)
    monkeypatch.setattr(encoder, "LocalEmbeddingEncoder", create_encoder)
    monkeypatch.setattr(pipeline, "MatchingPipeline", create_pipeline)
    assert runtime.get_pipeline() is configured
    assert runtime.get_pipeline() is configured
    assert calls == [(sessions, model, EXTRACTION_VERSION)]


@pytest.mark.parametrize("error", [ArgumentError(PRIVATE), ModuleNotFoundError(PRIVATE)])
def test_configured_factory_translates_database_configuration_failures(
    monkeypatch, empty_pipeline_cache, error
):
    from src.persistence import database

    monkeypatch.setenv("DATABASE_URL", "postgresql://synthetic/runtime_test")

    def create_engine():
        raise error

    monkeypatch.setattr(database, "create_db_engine", create_engine)
    with pytest.raises(DependencyUnavailableError):
        runtime.get_pipeline()


def test_configured_factory_handles_missing_database_configuration(
    monkeypatch, empty_pipeline_cache
):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DependencyUnavailableError):
        runtime.get_pipeline()
