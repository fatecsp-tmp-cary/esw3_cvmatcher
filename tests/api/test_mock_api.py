import json
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from src.mock_api.app import create_app
from src.schemas.candidate.curriculum import CurriculumRequest
from src.schemas.matches import MatchesResponse

_PROJECT_ROOT = Path(__file__).parents[2]
_SAMPLE_REQUEST = json.loads(
    (_PROJECT_ROOT / "examples/mock_api/curriculum.json").read_text(encoding="utf-8")
)


def test_mock_health_matches_public_health_shape() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_mock_matches_returns_ten_deterministic_sample_jobs_by_default() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/matches", json=_SAMPLE_REQUEST)

    assert response.status_code == 200
    matches = response.json()["matches"]
    assert len(matches) == 10
    assert [match["rank"] for match in matches] == list(range(1, 11))
    assert matches[0]["job"]["title"] == "Backend Developer 001"
    assert matches[0]["score"] == 100
    assert [match["job"]["id"] for match in matches] == list(range(1, 11))
    assert matches[0]["eligibility"] is True
    assert matches[0]["matched_skills"] == ["Python", "FastAPI"]
    assert matches[0]["missing_requirements"] == []


def test_mock_matches_limit_controls_response_sample_size() -> None:
    with TestClient(create_app()) as client:
        one_result = client.post("/matches?limit=1", json=_SAMPLE_REQUEST)
        all_results = client.post("/matches?limit=100", json=_SAMPLE_REQUEST)
        invalid_limit = client.post("/matches?limit=101", json=_SAMPLE_REQUEST)
        operation = client.get("/openapi.json").json()["paths"]["/matches"]["post"]

    assert one_result.status_code == 200
    assert len(one_result.json()["matches"]) == 1
    assert all_results.status_code == 200
    matches = all_results.json()["matches"]
    assert len(matches) == 100
    assert [match["rank"] for match in matches] == list(range(1, 101))
    assert len({match["job"]["job_url"] for match in matches}) == 100
    assert invalid_limit.status_code == 422
    assert [parameter["name"] for parameter in operation["parameters"]] == ["limit"]
    assert operation["parameters"][0]["schema"]["default"] == 10


def test_mock_validation_errors_do_not_echo_candidate_values() -> None:
    secret = "candidate-data-that-must-not-be-echoed"
    request = {**_SAMPLE_REQUEST, "curriculo_id": secret, "competencias": []}
    with TestClient(create_app()) as client:
        response = client.post("/matches", json=request)

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert secret not in response.text


def test_mock_openapi_and_swagger_ui_are_available() -> None:
    with TestClient(create_app()) as client:
        schema = client.get("/openapi.json")
        swagger = client.get("/docs")

    assert schema.status_code == 200
    operation = schema.json()["paths"]["/matches"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/CurriculumRequest"
    )
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/MatchesResponse"
    )
    assert swagger.status_code == 200
    assert "swagger-ui" in swagger.text


def test_mock_and_production_publish_identical_contract_components() -> None:
    from src.api.app import create_app as create_public_app

    with TestClient(create_app()) as mock, TestClient(create_public_app()) as public:
        mock_schemas = mock.get("/openapi.json").json()["components"]["schemas"]
        public_schemas = public.get("/openapi.json").json()["components"]["schemas"]

    for model in (CurriculumRequest, MatchesResponse):
        names = {model.__name__, *model.model_json_schema().get("$defs", {})}
        for name in names:
            assert mock_schemas[name] == public_schemas[name]


def test_mock_starts_without_database_libraries() -> None:
    # The mock Docker image installs only FastAPI and Uvicorn. Guard that path
    # in a fresh interpreter so cached imports cannot hide an ORM dependency.
    script = """
import importlib.abc
import sys

class BlockDatabaseImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'sqlalchemy', 'psycopg', 'pgvector', 'alembic'}:
            raise ImportError('Database library imported by mock: ' + fullname)

sys.meta_path.insert(0, BlockDatabaseImports())
from fastapi.testclient import TestClient
from src.mock_api.app import create_app

with TestClient(create_app()) as client:
    assert client.get('/health').json() == {'status': 'ok'}
    assert client.get('/openapi.json').status_code == 200
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=_PROJECT_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
