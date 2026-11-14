from fastapi.testclient import TestClient

from src.api.app import CURRICULUM_EXAMPLE, create_app


def test_internal_production_deadline_keeps_the_budget_outcome(monkeypatch, caplog):
    from src.api import runtime
    from src.processing import ProcessingUnavailable

    def pipeline(request, limit):
        raise ProcessingUnavailable("deadline")

    monkeypatch.setattr(runtime, "get_pipeline", lambda: pipeline)
    with (
        caplog.at_level("INFO", logger="src.api.app"),
        TestClient(create_app(runtime.production_matches)) as client,
    ):
        response = client.post("/matches", json=CURRICULUM_EXAMPLE)
    assert response.status_code == 503
    assert "matching_outcome=budget_exhausted" in caplog.text
    assert CURRICULUM_EXAMPLE["curriculo_id"] not in response.text + caplog.text
