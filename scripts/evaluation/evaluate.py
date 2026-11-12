"""Offline, exact-span evaluation of independently authored synthetic fixtures."""

import argparse
import json
import math
from pathlib import Path

CLASSES = {"REQUIRED", "PREFERRED", "NICE_TO_HAVE", None}
DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[2] / "tests/fixtures/matching/reviewed_cases.json"
)


def validate_spans(spans, description):
    if not isinstance(spans, list):
        raise ValueError("requirements must be a list")
    keys = []
    for span in spans:
        if set(span) != {"start", "end", "text", "requirement_class"}:
            raise ValueError("unexpected span fields")
        start, end = span["start"], span["end"]
        if (
            type(start) is not int
            or type(end) is not int
            or not 0 <= start < end <= len(description)
            or description[start:end] != span["text"]
            or span["requirement_class"] not in CLASSES
        ):
            raise ValueError("invalid exact span or requirement class")
        keys.append((start, end, span["requirement_class"]))
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate spans")
    return set(keys)


def validate_fixture(fixture):
    if fixture["schema_version"] != "1.0":
        raise ValueError("unsupported schema version")
    cases = fixture["cases"]
    expected_ids = {
        f"{lang}-{i:03d}" for lang, n in [("pt", 40), ("en", 10)] for i in range(1, n + 1)
    }
    if len(cases) != 50 or {c["id"] for c in cases} != expected_ids:
        raise ValueError("expected 50 stable IDs: 40 PT and 10 EN")
    for case in cases:
        if set(case) != {"id", "language", "synthetic", "tags", "job", "candidate", "expected"}:
            raise ValueError("unexpected case fields")
        if case["language"] != case["id"][:2] or case["synthetic"] is not True:
            raise ValueError("invalid language or provenance")
        if set(case["job"]) != {"title", "description", "skills"}:
            raise ValueError("unexpected job fields")
        candidate = case["candidate"]
        if set(candidate) != {"experiences", "education", "competencies"}:
            raise ValueError("unexpected candidate fields; identity is forbidden")
        for entry in candidate["experiences"]:
            if set(entry) != {"title", "description"}:
                raise ValueError("unexpected experience fields")
        for entry in candidate["education"]:
            if set(entry) != {"title"}:
                raise ValueError("unexpected education fields")
        if case["expected"]["role_relation"] not in {"relevant", "irrelevant"}:
            raise ValueError("invalid role relation")
        validate_spans(case["expected"]["requirements"], case["job"]["description"])
    return cases


def _metrics(tp, fp, fn):
    return {
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": tp / (tp + fp) if tp + fp else None,
        "recall": tp / (tp + fn) if tp + fn else None,
    }


def evaluate(fixture, predictions, *, case_ids=None):
    cases = validate_fixture(fixture)
    if case_ids is not None:
        selected = set(case_ids)
        known = {c["id"] for c in cases}
        if len(case_ids) != 25 or len(selected) != 25 or not selected <= known:
            raise ValueError("Expected one frozen 25-case partition")
        cases = [c for c in cases if c["id"] in selected]
        if sum(c["language"] == "pt" for c in cases) != 20:
            raise ValueError("Partition must contain 20 PT and 5 EN")
    provenance = fixture.get("provenance", {})
    reviewed = (
        provenance.get("kind") == "human-reviewed synthetic"
        and provenance.get("human_reviewed") is True
        and set(provenance.get("reviews", {})) == {c["id"] for c in fixture["cases"]}
    )
    heldout = (
        reviewed
        and case_ids is not None
        and set(case_ids) == set(provenance.get("partition", {}).get("heldout_ids", []))
    )
    if (
        set(predictions) != {"schema_version", "predictions"}
        or predictions["schema_version"] != "1.0"
    ):
        raise ValueError("unsupported predictions contract")
    by_id = {c["id"]: c for c in cases}
    supplied = {}
    for prediction in predictions["predictions"]:
        if set(prediction) != {"id", "requirements", "role_score"}:
            raise ValueError("unexpected prediction fields")
        case_id = prediction["id"]
        if case_id not in by_id or case_id in supplied:
            raise ValueError("unknown or duplicate prediction ID")
        score = prediction["role_score"]
        if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 100:
            raise ValueError("role_score must be finite and in [0,100]")
        validate_spans(prediction["requirements"], by_id[case_id]["job"]["description"])
        supplied[case_id] = prediction
    report = {
        "schema_version": "1.0",
        "dataset_kind": "human-reviewed synthetic" if reviewed else "agent-reviewed synthetic",
        "release_quality_measured": bool(heldout),
        "release_quality_approved": False,
        "groups": {},
    }
    for language in ("all", "pt", "en"):
        group = [c for c in cases if language == "all" or c["language"] == language]
        counts = {"exact_extraction": [0, 0, 0], "mandatory": [0, 0, 0], "field_spans": [0, 0, 0]}
        missing = []
        positive, negative = [], []
        correct = 0
        for case in group:
            gold = validate_spans(case["expected"]["requirements"], case["job"]["description"])
            prediction = supplied.get(case["id"])
            actual = set()
            if prediction is None:
                missing.append(case["id"])
            else:
                actual = validate_spans(prediction["requirements"], case["job"]["description"])
                relevant = case["expected"]["role_relation"] == "relevant"
                score = prediction["role_score"]
                (positive if relevant else negative).append(score)
                correct += (score >= 50) == relevant
            for metric in counts:
                expected = (
                    gold
                    if metric == "exact_extraction"
                    else {s for s in gold if s[2] == "REQUIRED"}
                )
                observed = (
                    actual
                    if metric == "exact_extraction"
                    else {s for s in actual if s[2] == "REQUIRED"}
                )
                if metric == "field_spans":
                    expected = {s[:2] for s in gold}
                    observed = {s[:2] for s in actual}
                values = (
                    len(expected & observed),
                    len(observed - expected),
                    len(expected - observed),
                )
                counts[metric] = [a + b for a, b in zip(counts[metric], values, strict=True)]
        pairs = len(positive) * len(negative)
        auc = (
            sum(1 if p > n else 0.5 if p == n else 0 for p in positive for n in negative) / pairs
            if pairs
            else None
        )
        metrics = {name: _metrics(*values) for name, values in counts.items()}
        mandatory = metrics["mandatory"]
        meets = (
            not missing
            and mandatory["precision"] is not None
            and mandatory["recall"] is not None
            and mandatory["precision"] >= 0.95
            and mandatory["recall"] >= 0.80
        )
        fields = metrics["field_spans"]
        field_met = (
            not missing
            and fields["precision"] is not None
            and fields["recall"] is not None
            and fields["precision"] >= 0.90
            and fields["recall"] >= 0.80
        )
        role_met = not missing and auc is not None and auc >= 0.90 and correct / len(group) >= 0.80
        report["groups"][language] = {
            "cases": len(group),
            "predictions": len(group) - len(missing),
            "missing_ids": missing,
            **metrics,
            "ranking": {
                "pairwise_auc_observed": auc,
                "observed_pairs": pairs,
                "role_accuracy_all_cases": correct / len(group),
                "complete": not missing,
            },
            "field_thresholds": {"precision": 0.90, "recall": 0.80, "targets_met": field_met},
            "semantic_role_thresholds": {
                "auc": 0.90,
                "accuracy": 0.80,
                "cutoff": 50,
                "targets_met": role_met,
            },
            "mandatory_thresholds": {
                "precision": 0.95,
                "recall": 0.80,
                "synthetic_gate_met": meets,
            },
        }
    report["heldout_targets_met"] = bool(
        heldout
        and all(
            group["field_thresholds"]["targets_met"]
            and group["semantic_role_thresholds"]["targets_met"]
            and group["mandatory_thresholds"]["synthetic_gate_met"]
            for name, group in report["groups"].items()
            if name in ("pt", "en")
        )
    )
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--partition", choices=("calibration", "heldout"))
    args = parser.parse_args(argv)
    try:
        fixture = json.loads(args.fixtures.read_text())
        ids = None
        if args.partition:
            provenance = fixture.get("provenance", {})
            if provenance.get("human_reviewed") is not True:
                raise ValueError("Partition evaluation requires validated human gold")
            ids = provenance["partition"][args.partition + "_ids"]
        report = evaluate(fixture, json.loads(args.predictions.read_text()), case_ids=ids)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
