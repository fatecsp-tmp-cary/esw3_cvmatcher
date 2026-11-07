import pytest
from pydantic import ValidationError

from src.schemas.matches import MatchesResponse


def _match():
    return {
        "rank": 1,
        "job": {
            "id": 42,
            "title": "Backend Engineer",
            "work_arrangement": "REMOTE",
            "skills": ["Python"],
        },
        "score": 87.5,
        "eligibility": True,
        "matched_skills": ["Python"],
        "missing_requirements": [],
        "embedding_model": "pending-model-selection",
        "algorithm_version": "v1",
    }


def test_matches_response_uses_approved_public_contract():
    response = MatchesResponse.model_validate({"matches": [_match()]})
    assert response.matches[0].job.id == 42
    assert set(response.model_dump(mode="json")["matches"][0]["job"]) == {
        "id",
        "company",
        "title",
        "description",
        "keywords",
        "location",
        "work_arrangement",
        "seniority_level",
        "skills",
        "salary",
        "currency",
        "job_url",
        "publication_date",
    }


@pytest.mark.parametrize("score", [-0.1, 100.1])
def test_matches_response_rejects_out_of_range_score(score):
    match = _match()
    match["score"] = score
    with pytest.raises(ValidationError) as error:
        MatchesResponse.model_validate({"matches": [match]})
    assert [e["loc"] for e in error.value.errors()] == [("matches", 0, "score")]


def test_matches_response_rejects_internal_job_fields():
    match = _match()
    match["job"]["source_job_id"] = "123"
    with pytest.raises(ValidationError) as error:
        MatchesResponse.model_validate({"matches": [match]})
    assert [e["loc"] for e in error.value.errors()] == [("matches", 0, "job", "source_job_id")]


@pytest.mark.parametrize("field", ["eligibility", "matched_skills", "missing_requirements"])
def test_match_details_are_required(field):
    match = _match()
    del match[field]
    with pytest.raises(ValidationError) as error:
        MatchesResponse.model_validate({"matches": [match]})
    assert [e["loc"] for e in error.value.errors()] == [("matches", 0, field)]
