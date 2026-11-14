"""Apply explicit user policy adjudications to copies, never model-derived gold.

The reviewed 2026-11-14 input remains unchanged. This operation is not a new
independent annotation. No model/classifier is imported to determine any label.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from scripts.evaluation.evaluate import validate_fixture, validate_spans

POLICY = "ADR-014-extraction-policy-2026-11-14"
# Explicit decisions on mentions omitted or inconsistently classified by the old
# convention. Source text is fixed, and every edit is verified against its input.
NULL_MENTIONS = {
    "pt-004": "Photoshop",
    "pt-007": "Espanhol",
    "pt-011": "Vue",
    "pt-017": "sênior",
    "pt-021": "Linux",
    "pt-030": "Photoshop",
    "pt-034": "SAP",
    "en-003": "Photoshop",
    "en-010": "Python",
}
PREFERRED_MENTIONS = {"pt-009": "NR35", "pt-014": "Power BI"}
# Retain the strongest actual occurrence, not a promoted first occurrence.
STRONGEST_OCCURRENCES = {"pt-031": "Python", "pt-032": "Docker", "en-005": "Java"}
RANK = {None: 0, "NICE_TO_HAVE": 1, "PREFERRED": 2, "REQUIRED": 3}


def update(source):
    validate_fixture(source)
    result = copy.deepcopy(source)
    changes = []
    for case in result["cases"]:
        before = copy.deepcopy(case["expected"])
        expected = case["expected"]
        rows = expected["requirements"]
        description = case["job"]["description"]
        case_id = case["id"]
        if case_id in NULL_MENTIONS:
            mention = NULL_MENTIONS[case_id]
            start = description.index(mention)
            rows[:] = [r for r in rows if r["start"] != start]
            rows.append(
                {
                    "text": mention,
                    "start": start,
                    "end": start + len(mention),
                    "requirement_class": None,
                }
            )
        if case_id in PREFERRED_MENTIONS:
            for row in rows:
                if row["text"] == PREFERRED_MENTIONS[case_id]:
                    row["requirement_class"] = "PREFERRED"
        if case_id in STRONGEST_OCCURRENCES:
            concept = STRONGEST_OCCURRENCES[case_id]
            matches = [r for r in rows if r["text"] == concept]
            winner = min(matches, key=lambda r: (-RANK[r["requirement_class"]], r["start"]))
            rows[:] = [r for r in rows if r["text"] != concept or r is winner]
        rows.sort(key=lambda r: (r["start"], r["end"]))
        if case_id in {"pt-038", "en-008"}:
            expected["role_relation"] = "irrelevant"
            expected["rationale"] = (
                "User policy: empty candidate evidence is irrelevant for role scoring; "
                "absence of job requirements does not establish relevance. "
                "Original rationale is retained in the source reviewed evidence."
            )
        if expected["requirements"] != before["requirements"]:
            expected["rationale"] = (
                "Original independent rationale and annotations are retained in the source. "
                "User-authorized ADR-014 policy adjudication: retain negated mentions as null, "
                "diferencial as PREFERRED, hedges as NICE_TO_HAVE, smallest entities, "
                "and strongest actual occurrence for repeated concepts. "
                "This update is not a new independent review."
            )
        validate_spans(rows, description)
        if expected != before:
            changes.append({"id": case_id, "before": before, "after": copy.deepcopy(expected)})
    result["provenance"].update(
        {
            "policy_adjudication": POLICY,
            "policy_adjudication_method": (
                "Explicit user decisions applied by assistant; no model labels"
            ),
            "labels_independently_reviewed_after_policy_change": False,
            "heldout_independent": False,
            "heldout_use": "regression/development only; previously used for diagnosis",
            "release_quality_measured": False,
            "release_quality_approved": False,
        }
    )
    validate_fixture(result)
    return result, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.source.read_text())
    updated, changes = update(source)
    args.output_directory.mkdir(parents=True, exist_ok=False)
    outputs = {
        "gold.json": updated,
        "changes.json": {
            "policy": POLICY,
            "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
            "source_unchanged": True,
            "changes": changes,
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "new_independent_human_review": False,
        },
    }
    partition = updated["provenance"]["partition"]
    for phase in ("calibration", "heldout"):
        outputs[f"{phase}.json"] = {
            "schema_version": "1.0",
            "policy": POLICY,
            "purpose": "calibration" if phase == "calibration" else "regression/development only",
            "new_independent_human_review": False,
            "cases": [c for c in updated["cases"] if c["id"] in partition[phase + "_ids"]],
        }
    for name, data in outputs.items():
        with (args.output_directory / name).open("x") as stream:
            stream.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"updated_cases": len(changes), "original_preserved": True}))


if __name__ == "__main__":
    main()
