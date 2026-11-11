"""Regression coverage for the shared public ranked response contract."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from src.schemas.matches import MatchesResponse


@pytest.fixture
def response_payload() -> dict:
    return {
        "matches": [
            {
                "rank": 1,
                "job": {"id": 42, "title": "Developer"},
                "score": 85.5,
                "eligibility": True,
                "matched_skills": [],
                "missing_requirements": [],
                "embedding_model": "synthetic-v1",
                "algorithm_version": "test-v1",
            }
        ]
    }


def test_empty_results_and_empty_details_are_valid(response_payload: dict) -> None:
    assert MatchesResponse.model_validate({"matches": []}).matches == []
    result = MatchesResponse.model_validate(response_payload).matches[0]
    assert result.job.id == 42
    assert result.matched_skills == result.missing_requirements == []


@pytest.mark.parametrize("score", [0, 100])
def test_inclusive_score_bounds(response_payload: dict, score: float) -> None:
    response_payload["matches"][0]["score"] = score
    assert MatchesResponse.model_validate(response_payload).matches[0].score == score


@pytest.mark.parametrize("score", [-0.01, 100.01, float("nan"), float("inf"), -float("inf")])
def test_invalid_score_is_rejected(response_payload: dict, score: float) -> None:
    response_payload["matches"][0]["score"] = score
    with pytest.raises(ValidationError) as error:
        MatchesResponse.model_validate(response_payload)
    assert error.value.errors()[0]["loc"] == ("matches", 0, "score")


@pytest.mark.parametrize("job_id", [0, -1, None, "invalid"])
def test_invalid_job_identity_is_rejected(response_payload: dict, job_id: object) -> None:
    response_payload["matches"][0]["job"]["id"] = job_id
    with pytest.raises(ValidationError) as error:
        MatchesResponse.model_validate(response_payload)
    assert error.value.errors()[0]["loc"] == ("matches", 0, "job", "id")


def test_missing_job_identity_is_rejected(response_payload: dict) -> None:
    del response_payload["matches"][0]["job"]["id"]
    with pytest.raises(ValidationError) as error:
        MatchesResponse.model_validate(response_payload)
    assert error.value.errors()[0]["loc"] == ("matches", 0, "job", "id")


@pytest.mark.parametrize(
    "field",
    [
        "rank",
        "job",
        "score",
        "eligibility",
        "matched_skills",
        "missing_requirements",
        "embedding_model",
        "algorithm_version",
    ],
)
def test_required_match_fields_cannot_be_omitted(response_payload: dict, field: str) -> None:
    del response_payload["matches"][0][field]
    with pytest.raises(ValidationError) as error:
        MatchesResponse.model_validate(response_payload)
    assert error.value.errors()[0]["loc"] == ("matches", 0, field)
    assert error.value.errors()[0]["type"] == "missing"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rank", 0),
        ("eligibility", None),
        ("eligibility", "unknown"),
        ("embedding_model", None),
        ("embedding_model", 123),
        ("algorithm_version", None),
        ("algorithm_version", 123),
    ],
)
def test_invalid_match_metadata_is_rejected(
    response_payload: dict, field: str, value: object
) -> None:
    response_payload["matches"][0][field] = value
    with pytest.raises(ValidationError) as error:
        MatchesResponse.model_validate(response_payload)
    assert error.value.errors()[0]["loc"] == ("matches", 0, field)


@pytest.mark.parametrize("field", ["matched_skills", "missing_requirements"])
@pytest.mark.parametrize("value", [None, "Python", [None]])
def test_details_must_be_string_arrays(response_payload: dict, field: str, value: object) -> None:
    response_payload["matches"][0][field] = value
    with pytest.raises(ValidationError):
        MatchesResponse.model_validate(response_payload)


@pytest.mark.parametrize("level", ["response", "match", "job"])
def test_curriculum_uuid_cannot_enter_response(response_payload: dict, level: str) -> None:
    payload = deepcopy(response_payload)
    target = {
        "response": payload,
        "match": payload["matches"][0],
        "job": payload["matches"][0]["job"],
    }[level]
    target["curriculo_id"] = "550e8400-e29b-41d4-a716-446655440000"
    with pytest.raises(ValidationError) as error:
        MatchesResponse.model_validate(payload)
    assert error.value.errors()[0]["type"] == "extra_forbidden"
