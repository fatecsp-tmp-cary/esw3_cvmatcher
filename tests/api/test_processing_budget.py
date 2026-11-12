from copy import deepcopy

from fastapi.testclient import TestClient

from src.api.app import CURRICULUM_EXAMPLE, create_app
from src.api.errors import DependencyUnavailableError
from src.processing import RequestBudget
from src.schemas.matches import MatchesResponse


def payload():
    result = deepcopy(CURRICULUM_EXAMPLE)
    result["experiencias"][0]["empresa"] = "candidate-private-canary"
    return result


def test_busy_request_returns_safe_503_without_executing_or_losing_the_active_slot(caplog):
    budget = RequestBudget()
    calls = []

    def execute(request, limit):
        calls.append(limit)
        return MatchesResponse(matches=[])

    with (
        caplog.at_level("INFO", logger="src.api.app"),
        TestClient(create_app(execute, request_budget=budget)) as client,
    ):
        with budget.admit():
            for _ in range(2):
                response = client.post("/matches", json=payload())
                assert response.status_code == 503
                assert "candidate-private-canary" not in response.text
            assert calls == []
        assert client.post("/matches", json=payload()).status_code == 200
    assert calls == [10]
    assert "matching_outcome=budget_exhausted" in caplog.text
    assert "candidate-private-canary" not in caplog.text


def test_exact_deadline_returns_safe_503_then_allows_a_new_request(caplog):
    now = [0.0]
    calls = []

    def execute(request, limit):
        if not calls:
            now[0] = 30.0
        calls.append(limit)
        return MatchesResponse(matches=[])

    with caplog.at_level("INFO", logger="src.api.app"):
        app = create_app(execute, request_budget=RequestBudget(clock=lambda: now[0]))
        with TestClient(app) as client:
            assert client.post("/matches", json=payload()).status_code == 503
            assert client.post("/matches", json=payload()).status_code == 200
    assert "matching_outcome=budget_exhausted" in caplog.text
    assert "matching_outcome=empty" in caplog.text
    assert "candidate-private-canary" not in caplog.text


def test_dependency_failure_is_timed_with_fixed_status_and_no_candidate_values(caplog):
    ticks = iter([10.0, 10.125])

    def execute(request, limit):
        raise DependencyUnavailableError("candidate-private-canary")

    with (
        caplog.at_level("INFO", logger="src.api.app"),
        TestClient(create_app(execute, request_clock=lambda: next(ticks))) as client,
    ):
        response = client.post("/matches", json=payload())
    assert response.status_code == 503
    assert "matching_request_duration_ms=125.000 matching_outcome=unavailable" in caplog.text
    assert "candidate-private-canary" not in response.text + caplog.text


def test_unconfigured_executor_is_timed_as_unavailable(caplog):
    ticks = iter([10.0, 10.125])
    with (
        caplog.at_level("INFO", logger="src.api.app"),
        TestClient(create_app(request_clock=lambda: next(ticks))) as client,
    ):
        response = client.post("/matches", json=payload())
    assert response.status_code == 503
    assert "matching_request_duration_ms=125.000 matching_outcome=unavailable" in caplog.text
    assert "candidate-private-canary" not in response.text + caplog.text
