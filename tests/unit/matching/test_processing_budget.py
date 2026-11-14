from threading import Event

import pytest

from src.processing import ProcessingUnavailable, RequestBudget, checkpoint


def test_busy_request_does_not_queue_or_release_the_active_slot():
    budget = RequestBudget()
    with budget.admit():
        for _ in range(2):
            with pytest.raises(ProcessingUnavailable, match="busy"), budget.admit():
                pytest.fail("busy work must not execute")
    with budget.admit():
        checkpoint()


def test_exact_deadline_cancels_and_releases_slot_without_a_wall_clock_wait():
    now = [100.0]
    budget = RequestBudget(clock=lambda: now[0])
    with pytest.raises(ProcessingUnavailable, match="deadline"), budget.admit():
        now[0] = 129.999
        checkpoint()
        now[0] = 130.0
        checkpoint()
    with budget.admit():
        checkpoint()


def test_cancellation_and_dependency_failure_release_only_after_work_unwinds():
    budget = RequestBudget()
    cancelled = Event()
    with pytest.raises(ProcessingUnavailable, match="cancelled"), budget.admit(cancelled=cancelled):
        cancelled.set()
        checkpoint()
    with pytest.raises(RuntimeError, match="synthetic"), budget.admit():
        raise RuntimeError("synthetic dependency failure")
    with budget.admit():
        checkpoint()


@pytest.mark.parametrize("outcome", ["success", "empty", "unavailable"])
def test_pipeline_telemetry_is_fixed_category_and_omits_candidate_values(
    outcome, monkeypatch, caplog
):
    from src.matching.pipeline import MatchingPipeline
    from src.schemas.matches import MatchesResponse

    pipeline = object.__new__(MatchingPipeline)
    instants = iter([1.0, 1.125])
    monkeypatch.setattr("src.matching.pipeline.time.perf_counter", lambda: next(instants))

    class Result:
        matches = [object()] if outcome == "success" else []

    def match(request, limit):
        if outcome == "unavailable":
            raise ValueError("candidate-private-canary")
        return Result() if outcome == "success" else MatchesResponse(matches=[])

    monkeypatch.setattr(pipeline, "_match", match)
    with caplog.at_level("INFO", logger="src.matching.pipeline"):
        if outcome == "unavailable":
            with pytest.raises(ValueError):
                pipeline("candidate-private-canary", 10)
        else:
            pipeline("candidate-private-canary", 10)
    assert "matching_duration_ms=125.000" in caplog.text
    assert f"matching_outcome={outcome}" in caplog.text
    assert "candidate-private-canary" not in caplog.text
