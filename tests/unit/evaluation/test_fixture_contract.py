"""Contract and evaluator tests; oracle round trips test plumbing, not model quality."""

import copy
import json

import pytest
from scripts.evaluation.evaluate import DEFAULT_FIXTURE, evaluate, main, validate_fixture


@pytest.fixture
def fixture():
    return json.loads(DEFAULT_FIXTURE.read_text())


def oracle(fixture):
    return {
        "schema_version": "1.0",
        "predictions": [
            {
                "id": c["id"],
                "requirements": copy.deepcopy(c["expected"]["requirements"]),
                "role_score": 100 if c["expected"]["role_relation"] == "relevant" else 0,
            }
            for c in fixture["cases"]
        ],
    }


def test_fixture_contract(fixture):
    cases = validate_fixture(fixture)
    assert len(cases) == 50
    assert sum(c["language"] == "pt" for c in cases) == 40
    assert sum(c["language"] == "en" for c in cases) == 10
    assert fixture["provenance"] == {
        "kind": "agent-reviewed synthetic",
        "reviewer": "independent evaluation2 agent",
        "labels_before_model_outputs": True,
        "human_reviewed": False,
        "release_quality_measured": False,
    }
    assert {s["requirement_class"] for c in cases for s in c["expected"]["requirements"]} == {
        "REQUIRED",
        "PREFERRED",
        "NICE_TO_HAVE",
        None,
    }
    tags = {t for c in cases for t in c["tags"]}
    assert {
        "negation",
        "uncertainty",
        "conflict",
        "long_text",
        "seniority",
        "empty_evidence",
    } <= tags
    for language in ("pt", "en"):
        group = [c for c in cases if c["language"] == language]
        assert {c["expected"]["role_relation"] for c in group} == {"relevant", "irrelevant"}
        assert any(len(c["job"]["description"]) > 4000 for c in group)


@pytest.mark.parametrize("mutation", ["offset", "vocabulary", "identity", "id", "language"])
def test_reject_invalid_fixture(fixture, mutation):
    case = fixture["cases"][0]
    if mutation == "offset":
        case["expected"]["requirements"][0]["start"] += 1
    elif mutation == "vocabulary":
        case["expected"]["requirements"][0]["requirement_class"] = "MANDATORY"
    elif mutation == "identity":
        case["candidate"]["uuid"] = "forbidden"
    elif mutation == "id":
        case["id"] = fixture["cases"][1]["id"]
    else:
        case["language"] = "en"
    with pytest.raises(ValueError):
        validate_fixture(fixture)


def test_oracle_round_trip_only_checks_evaluator(fixture):
    report = evaluate(fixture, oracle(fixture))
    for group in report["groups"].values():
        assert group["exact_extraction"]["precision"] == 1
        assert group["mandatory"]["recall"] == 1
        assert group["ranking"]["pairwise_auc_observed"] == 1
        assert group["mandatory_thresholds"]["synthetic_gate_met"] is True
    assert report["release_quality_measured"] is False


def test_missing_predictions_are_false_negatives(fixture):
    report = evaluate(fixture, {"schema_version": "1.0", "predictions": []})
    for group in report["groups"].values():
        assert len(group["missing_ids"]) == group["cases"]
        assert group["exact_extraction"]["false_negative"] > 0
        assert group["mandatory"]["precision"] is None
        assert group["mandatory"]["recall"] == 0
        assert group["ranking"]["pairwise_auc_observed"] is None
        assert group["ranking"]["role_accuracy_all_cases"] == 0
        assert group["mandatory_thresholds"]["synthetic_gate_met"] is False


def test_partial_coverage_per_language(fixture):
    predictions = oracle(fixture)
    predictions["predictions"] = predictions["predictions"][:40]
    report = evaluate(fixture, predictions)["groups"]
    assert report["pt"]["predictions"] == 40
    assert report["en"]["predictions"] == 0
    assert report["all"]["mandatory_thresholds"]["synthetic_gate_met"] is False


def test_wrong_class_is_false_positive_and_false_negative(fixture):
    predictions = oracle(fixture)
    predictions["predictions"][0]["requirements"][0]["requirement_class"] = "PREFERRED"
    result = evaluate(fixture, predictions)["groups"]["all"]
    assert result["exact_extraction"]["false_positive"] == 1
    assert result["exact_extraction"]["false_negative"] == 1
    assert result["mandatory"]["false_negative"] == 1


def test_ties_and_reversed_ranking(fixture):
    predictions = oracle(fixture)
    for p in predictions["predictions"]:
        p["role_score"] = 50
    assert (
        evaluate(fixture, predictions)["groups"]["all"]["ranking"]["pairwise_auc_observed"] == 0.5
    )
    predictions = oracle(fixture)
    for p in predictions["predictions"]:
        p["role_score"] = 100 - p["role_score"]
    assert evaluate(fixture, predictions)["groups"]["all"]["ranking"]["pairwise_auc_observed"] == 0


@pytest.mark.parametrize("mutation", ["unknown", "duplicate", "nan", "bool", "span"])
def test_reject_invalid_predictions(fixture, mutation):
    predictions = oracle(fixture)
    first = predictions["predictions"][0]
    if mutation == "unknown":
        first["id"] = "unknown"
    elif mutation == "duplicate":
        predictions["predictions"].append(copy.deepcopy(first))
    elif mutation == "nan":
        first["role_score"] = float("nan")
    elif mutation == "bool":
        first["role_score"] = True
    else:
        first["requirements"][0]["end"] += 1
    with pytest.raises(ValueError):
        evaluate(fixture, predictions)


def test_cli_missing_predictions(fixture, tmp_path, capsys):
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"schema_version": "1.0", "predictions": []}))
    assert main(["--predictions", str(path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["groups"]["all"]["predictions"] == 0


def test_cli_invalid_json(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("invalid")
    with pytest.raises(SystemExit) as exc:
        main(["--predictions", str(path)])
    assert exc.value.code == 2
