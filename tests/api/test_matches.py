from fastapi.testclient import TestClient

from src.api.app import create_app
from src.schemas.candidate import CandidateProfile
from src.schemas.matches import MatchesResponse

_CANDIDATE = {"skills": ["Python"], "job_titles": ["Developer"]}
_RESULT = {
    "matches": [
        {
            "rank": 1,
            "job": {
                "company": None,
                "title": "Backend Developer",
                "description": None,
                "keywords": None,
                "location": None,
                "work_arrangement": None,
                "seniority_level": None,
                "skills": ["Python"],
                "salary": None,
                "currency": None,
                "job_url": None,
                "publication_date": None,
            },
            "score": 87.5,
            "embedding_model": "pending-model-selection",
            "algorithm_version": "v1",
        }
    ]
}


class _Executor:
    def __init__(self) -> None:
        self.received: CandidateProfile | None = None

    async def execute(self, candidate: CandidateProfile) -> MatchesResponse:
        self.received = candidate
        return MatchesResponse.model_validate(_RESULT)


def test_matches_accepts_canonical_candidate_profile_directly() -> None:
    executor = _Executor()
    with TestClient(create_app(executor)) as client:
        response = client.post("/matches", json=_CANDIDATE)

    assert response.status_code == 200
    assert response.json() == _RESULT
    assert executor.received is not None
    assert executor.received.job_titles == ["Developer"]


def test_matches_rejects_invalid_candidate_without_echoing_values() -> None:
    with TestClient(create_app(_Executor())) as client:
        response = client.post("/matches", json={"skills": ["private-cv-value"]})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert "private-cv-value" not in response.text


def test_matches_reports_unavailable_when_executor_is_not_configured() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/matches", json=_CANDIDATE)

    assert response.status_code == 503
    assert response.json()["status"] == 503


def test_matches_openapi_uses_direct_candidate_and_ranked_response_schemas() -> None:
    schema = create_app().openapi()
    operation = schema["paths"]["/matches"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/CandidateProfile"
    )
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/MatchesResponse")
