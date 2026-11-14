"""Policy adjudication cannot renew held-out independence or rewrite its source."""

import copy
import json
from pathlib import Path

from scripts.evaluation.evaluate import evaluate
from scripts.evaluation.update_extraction_policy_labels import update

DIRECTORY = Path(__file__).resolve().parents[3] / "docs/match/human-review/extraction-policy-v2"


def test_policy_updates_are_explicit_and_preserve_synthetic_inputs_and_originals():
    updated = json.loads((DIRECTORY / "gold.json").read_text())
    changes = json.loads((DIRECTORY / "changes.json").read_text())
    assert len(changes["changes"]) == 16
    assert changes["new_independent_human_review"] is False
    by_id = {case["id"]: case for case in updated["cases"]}
    assert by_id["en-003"]["expected"]["requirements"][1]["requirement_class"] is None
    assert len(by_id["pt-032"]["expected"]["requirements"]) == 1
    assert by_id["pt-032"]["expected"]["requirements"][0]["start"] == 20
    assert by_id["pt-009"]["expected"]["requirements"][1]["requirement_class"] == "PREFERRED"
    original = copy.deepcopy(updated)
    for change in changes["changes"]:
        next(c for c in original["cases"] if c["id"] == change["id"])["expected"] = change["before"]
    saved = copy.deepcopy(original)
    regenerated, _ = update(original)
    assert original == saved
    assert [c["expected"] for c in regenerated["cases"]] == [
        c["expected"] for c in updated["cases"]
    ]
    for before, after in zip(original["cases"], regenerated["cases"], strict=True):
        assert before["job"] == after["job"] and before["candidate"] == after["candidate"]


def test_oracle_regression_never_claims_independent_acceptance():
    fixture = json.loads((DIRECTORY / "gold.json").read_text())
    ids = fixture["provenance"]["partition"]["heldout_ids"]
    predictions = {
        "schema_version": "1.0",
        "predictions": [
            {
                "id": c["id"],
                "requirements": c["expected"]["requirements"],
                "role_score": 100 if c["expected"]["role_relation"] == "relevant" else 0,
            }
            for c in fixture["cases"]
            if c["id"] in ids
        ],
    }
    report = evaluate(fixture, predictions, case_ids=ids)
    assert report["groups"]["pt"]["field_thresholds"]["targets_met"]
    assert not report["heldout_targets_met"] and not report["release_quality_measured"]
    assert not report["heldout_independent"] and not report["release_quality_approved"]
