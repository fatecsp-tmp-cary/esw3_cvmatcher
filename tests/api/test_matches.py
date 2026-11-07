from fastapi.testclient import TestClient

from src.api.app import CURRICULUM_EXAMPLE, create_app
from src.normalization.candidate.curriculum import to_candidate_profile
from src.schemas.matches import MatchesResponse


def test_curriculum_executor_can_adapt_profile_without_changing_the_public_boundary():
    received = []

    def execute(curriculum, limit):
        received.append((to_candidate_profile(curriculum), limit))
        return MatchesResponse(matches=[])

    with TestClient(create_app(execute)) as client:
        response = client.post("/matches?limit=5", json=CURRICULUM_EXAMPLE)

    assert response.status_code == 200
    assert response.json() == {"matches": []}
    profile, limit = received[0]
    assert profile.skills == ["Python"]
    assert profile.experience[0].start_date == "2025-01-01"
    assert profile.academic_projects[0].technologies == "Java, Clean Architecture, Docker"
    assert "curriculo_id" not in profile.model_dump()
    assert limit == 5
