import pytest
from pydantic import ValidationError

from src.schemas.matches import MatchesResponse


def test_matches_response_uses_approved_public_contract():
    response = MatchesResponse.model_validate(
        {
            "matches": [
                {
                    "rank": 1,
                    "job": {
                        "title": "Backend Engineer",
                        "work_arrangement": "REMOTE",
                        "skills": ["Python"],
                    },
                    "score": 87.5,
                    "embedding_model": "pending-model-selection",
                    "algorithm_version": "v1",
                }
            ]
        }
    )

    assert response.matches[0].rank == 1
    assert response.matches[0].job.title == "Backend Engineer"
    assert set(response.model_dump(mode="json")["matches"][0]["job"]) == {
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
    with pytest.raises(ValidationError):
        MatchesResponse.model_validate(
            {
                "matches": [
                    {
                        "rank": 1,
                        "job": {"title": "Backend Engineer"},
                        "score": score,
                        "embedding_model": "model",
                        "algorithm_version": "v1",
                    }
                ]
            }
        )


def test_matches_response_rejects_internal_job_fields():
    with pytest.raises(ValidationError):
        MatchesResponse.model_validate(
            {
                "matches": [
                    {
                        "rank": 1,
                        "job": {"title": "Backend Engineer", "source_job_id": "123"},
                        "score": 90,
                        "embedding_model": "model",
                        "algorithm_version": "v1",
                    }
                ]
            }
        )
