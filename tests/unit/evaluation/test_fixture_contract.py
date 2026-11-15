"""Contract and evaluator tests; oracle round trips test plumbing, not model quality."""

import copy
import json
from pathlib import Path

import pytest
from scripts.evaluation.evaluate import (
    CURRENT_REVIEW_POLICY,
    DEFAULT_FIXTURE,
    evaluate,
    main,
    validate_fixture,
)


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


@pytest.mark.parametrize(
    "mutation",
    ["missing", "null", "kind", "reviewer", "labels", "human", "measured", "approved"],
)
def test_evaluation_rejects_missing_or_false_agent_provenance(fixture, mutation):
    if mutation == "missing":
        fixture.pop("provenance")
    elif mutation == "null":
        fixture["provenance"] = None
    else:
        field, value = {
            "kind": ("kind", "unreviewed"),
            "reviewer": ("reviewer", " "),
            "labels": ("labels_before_model_outputs", False),
            "human": ("human_reviewed", True),
            "measured": ("release_quality_measured", True),
            "approved": ("release_quality_approved", True),
        }[mutation]
        fixture["provenance"][field] = value
    with pytest.raises(ValueError, match="provenance"):
        evaluate(fixture, oracle(fixture))


@pytest.fixture
def human_fixture(fixture):
    # Synthetic metadata exercises the promotion format, never actual annotations.
    partition_path = Path(__file__).resolve().parents[3] / "docs/match/human-review/partition.json"
    partition = json.loads(partition_path.read_text())
    fixture["provenance"] = {
        "kind": "human-reviewed synthetic",
        "human_reviewed": True,
        "release_quality_measured": False,
        "release_quality_approved": False,
        "source_sha256": partition["source_sha256"],
        "partition": partition,
        "reviews": {
            case["id"]: {
                "reviewer": "synthetic-validation-only",
                "reviewed_at": "2026-11-12T00:00:00Z",
            }
            for case in fixture["cases"]
        },
    }
    return fixture


@pytest.mark.parametrize(
    "mutation",
    ["review", "reviewer", "timestamp", "timezone", "hash", "partition", "overlap", "duplicate"],
)
def test_invalid_review_records_cannot_claim_release_measurement(human_fixture, mutation):
    provenance = human_fixture["provenance"]
    ids = provenance["partition"]["heldout_ids"]
    review = provenance["reviews"][ids[0]]
    if mutation == "review":
        provenance["reviews"][ids[0]] = None
    elif mutation == "reviewer":
        review["reviewer"] = ""
    elif mutation == "timestamp":
        review["reviewed_at"] = "not a timestamp"
    elif mutation == "timezone":
        review["reviewed_at"] = "2026-11-12T00:00:00"
    elif mutation == "hash":
        provenance["source_sha256"] = "invalid"
    elif mutation == "partition":
        provenance["partition"] = {"heldout_ids": ids}
    elif mutation == "overlap":
        provenance["partition"]["calibration_ids"] = list(ids)
    else:
        provenance["partition"]["calibration_ids"][0] = provenance["partition"]["calibration_ids"][
            1
        ]
    with pytest.raises(ValueError):
        evaluate(human_fixture, {"schema_version": "1.0", "predictions": []}, case_ids=ids)


def test_policy_adjudication_cannot_restore_independence_by_omitting_flags(human_fixture):
    human_fixture["provenance"].update(
        {
            "policy_adjudication": "synthetic-policy-test",
            "policy_adjudication_method": "synthetic test metadata only",
            "heldout_use": "regression only",
        }
    )
    with pytest.raises(ValueError, match="regression-only"):
        validate_fixture(human_fixture)


def test_legacy_promoted_gold_is_valid_regression_without_fresh_independence(human_fixture):
    ids = human_fixture["provenance"]["partition"]["heldout_ids"]
    report = evaluate(human_fixture, {"schema_version": "1.0", "predictions": []}, case_ids=ids)
    assert report["dataset_kind"] == "human-reviewed synthetic"
    assert not report["heldout_independent"] and not report["release_quality_measured"]


@pytest.mark.parametrize("policy_metadata", ["original", "removed", "explicit-fresh-claim"])
def test_known_reused_corpus_cannot_regain_independent_acceptance(policy_metadata):
    directory = Path(__file__).resolve().parents[3] / "docs/match/human-review/extraction-policy-v2"
    name = "source-reviewed-gold.json" if policy_metadata == "original" else "gold.json"
    fixture = json.loads((directory / name).read_text())
    provenance = fixture["provenance"]
    if policy_metadata != "original":
        for field in (
            "policy_adjudication",
            "policy_adjudication_method",
            "heldout_use",
            "heldout_independent",
            "labels_independently_reviewed_after_policy_change",
        ):
            provenance.pop(field, None)
    if policy_metadata == "explicit-fresh-claim":
        provenance.update(
            {
                "heldout_independent": True,
                "labels_independently_reviewed_after_policy_change": True,
                "independence_policy": CURRENT_REVIEW_POLICY,
            }
        )
    ids = provenance["partition"]["heldout_ids"]
    report = evaluate(fixture, {"schema_version": "1.0", "predictions": []}, case_ids=ids)
    assert not report["heldout_independent"] and not report["release_quality_measured"]
    assert not report["release_quality_approved"]


@pytest.mark.parametrize("missing", ["policy", "heldout", "labels", "old-policy", None])
def test_new_source_requires_explicit_current_policy_independence(human_fixture, missing):
    # A synthetic metadata probe tests interpretation, never annotation quality.
    provenance = human_fixture["provenance"]
    provenance.update(
        {
            "source_sha256": "1" * 64,
            "heldout_independent": True,
            "labels_independently_reviewed_after_policy_change": True,
            "independence_policy": CURRENT_REVIEW_POLICY,
        }
    )
    provenance["partition"]["source_sha256"] = provenance["source_sha256"]
    if missing == "old-policy":
        provenance["independence_policy"] = "ADR-008"
    elif missing is not None:
        field = {
            "policy": "independence_policy",
            "heldout": "heldout_independent",
            "labels": "labels_independently_reviewed_after_policy_change",
        }[missing]
        provenance.pop(field)
    ids = provenance["partition"]["heldout_ids"]
    report = evaluate(human_fixture, {"schema_version": "1.0", "predictions": []}, case_ids=ids)
    assert report["release_quality_measured"] is (missing is None)
    assert not report["heldout_targets_met"] and not report["release_quality_approved"]


def test_cli_rejects_null_provenance_before_reading_partition(fixture, tmp_path):
    fixture["provenance"] = None
    fixture_path = tmp_path / "invalid-fixture.json"
    fixture_path.write_text(json.dumps(fixture))
    predictions = tmp_path / "predictions.json"
    predictions.write_text(json.dumps({"schema_version": "1.0", "predictions": []}))
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "--fixtures",
                str(fixture_path),
                "--predictions",
                str(predictions),
                "--partition",
                "heldout",
            ]
        )
    assert exc.value.code == 2


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
