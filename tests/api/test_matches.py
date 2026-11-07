from fastapi.testclient import TestClient

from src.api.app import CURRICULUM_EXAMPLE, create_app
from src.schemas.candidate.curriculum import CurriculumRequest
from src.schemas.matches import MatchesResponse


def test_ranked_response_executor_keeps_the_curriculum_and_limit_boundary():
    received = []

    def execute(curriculum, limit):
        assert isinstance(curriculum, CurriculumRequest)
        received.append((curriculum, limit))
        return MatchesResponse(matches=[])

    with TestClient(create_app(execute)) as client:
        response = client.post("/matches?limit=5", json=CURRICULUM_EXAMPLE)

    assert response.status_code == 200
    assert response.json() == {"matches": []}
    request, limit = received[0]
    assert request.experiencias[0].inicio.isoformat() == "2025-01-01"
    assert str(request.curriculo_id) not in response.text
    assert limit == 5
