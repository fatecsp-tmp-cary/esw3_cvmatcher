"""Validate independent blind annotations without claiming release quality."""

import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts.evaluation.evaluate import validate_fixture, validate_spans

ROOT = Path(__file__).resolve().parents[2]


def promote(source, partition, packets, *, source_sha256):
    """Require unchanged synthetic inputs and complete independent review records."""
    source_cases = {case["id"]: case for case in validate_fixture(source)}
    if partition["source_sha256"] != source_sha256:
        raise ValueError("Partition source hash mismatch")
    calibration = set(partition["calibration_ids"])
    heldout = set(partition["heldout_ids"])
    if calibration & heldout or calibration | heldout != source_cases.keys():
        raise ValueError("Invalid or overlapping evaluation partition")
    for ids in (calibration, heldout):
        if len(ids) != 25 or sum(source_cases[i]["language"] == "pt" for i in ids) != 20:
            raise ValueError("Each partition must contain 20 PT and 5 EN cases")
    reviewed = {}
    for packet, ids in zip(packets, (calibration, heldout), strict=True):
        if packet["source_sha256"] != source_sha256:
            raise ValueError("Review source hash mismatch")
        cases = packet["cases"]
        if len(cases) != len(ids) or {c["id"] for c in cases} != ids:
            raise ValueError("Missing, duplicate or misplaced review cases")
        for case in cases:
            original = source_cases[case["id"]]
            if any(case[name] != original[name] for name in ("job", "candidate", "language")):
                raise ValueError("Blind review changed original inputs")
            review = case["review"]
            if review["status"] != "reviewed" or review.get("uncertainties"):
                raise ValueError("Review is pending or requires adjudication")
            if not isinstance(review["reviewer"], str) or not review["reviewer"].strip():
                raise ValueError("Reviewer identifier is required")
            instant = datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
            if instant.tzinfo is None:
                raise ValueError("Review timestamp must include timezone")
            if review["role_relation"] not in {"relevant", "irrelevant"}:
                raise ValueError("Role relation is not reviewed")
            if not isinstance(review["rationale"], str) or not review["rationale"].strip():
                raise ValueError("Independent rationale is required")
            validate_spans(review["requirements"], original["job"]["description"])
            reviewed[case["id"]] = review
    result = copy.deepcopy(source)
    result["provenance"] = {
        "kind": "human-reviewed synthetic",
        "human_reviewed": True,
        "release_quality_measured": False,
        "release_quality_approved": False,
        "source_sha256": source_sha256,
        "partition": partition,
    }
    for case in result["cases"]:
        review = reviewed[case["id"]]
        case["expected"] = {
            "role_relation": review["role_relation"],
            "requirements": review["requirements"],
            "rationale": review["rationale"],
        }
        case["human_review"] = {
            "reviewer": review["reviewer"],
            "reviewed_at": review["reviewed_at"],
        }
        # Keep the established case contract; review provenance is separate.
        result["provenance"].setdefault("reviews", {})[case["id"]] = case.pop("human_review")
    validate_fixture(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--heldout", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source_path = ROOT / "tests/fixtures/matching/reviewed_cases.json"
    result = promote(
        json.loads(source_path.read_text()),
        json.loads((ROOT / "docs/match/human-review/partition.json").read_text()),
        [json.loads(args.calibration.read_text()), json.loads(args.heldout.read_text())],
        source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
    )
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
