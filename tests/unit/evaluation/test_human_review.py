"""Synthetic oracle records test validation, never actual human review quality."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from scripts.evaluation.evaluate import DEFAULT_FIXTURE
from scripts.evaluation.promote_review import promote

ROOT = Path(__file__).resolve().parents[3]


def documents():
    source = json.loads(DEFAULT_FIXTURE.read_text())
    directory = ROOT / "docs/match/human-review"
    partition = json.loads((directory / "partition.json").read_text())
    packets = [
        json.loads((directory / f"{name}.json").read_text()) for name in ("calibration", "heldout")
    ]
    return source, partition, packets, hashlib.sha256(DEFAULT_FIXTURE.read_bytes()).hexdigest()


def test_pending_or_changed_blind_packets_cannot_be_promoted():
    source, partition, packets, digest = documents()
    with pytest.raises(ValueError, match="pending"):
        promote(source, partition, packets, source_sha256=digest)
    packets[0]["cases"][0]["job"]["title"] = "modified"
    with pytest.raises(ValueError, match="changed original inputs"):
        promote(source, partition, packets, source_sha256=digest)


def test_complete_synthetic_oracle_checks_plumbing_without_approving_release():
    source, partition, packets, digest = documents()
    by_id = {case["id"]: case for case in source["cases"]}
    for packet in packets:
        for case in packet["cases"]:
            expected = by_id[case["id"]]["expected"]
            case["review"] = {
                "status": "reviewed",
                "reviewer": "synthetic-test-oracle",
                "reviewed_at": "2026-11-12T00:00:00Z",
                "uncertainties": None,
                "role_relation": expected["role_relation"],
                "requirements": copy.deepcopy(expected["requirements"]),
                "rationale": "Synthetic validation plumbing only, not human labels.",
            }
    result = promote(source, partition, packets, source_sha256=digest)
    assert result["provenance"]["human_reviewed"] is True
    assert result["provenance"]["release_quality_measured"] is False
    assert result["provenance"]["release_quality_approved"] is False
    assert source["provenance"]["human_reviewed"] is False
    assert len(result["provenance"]["reviews"]) == 50
    packets[0]["cases"][0]["review"]["requirements"][0]["start"] += 1
    with pytest.raises(ValueError, match="span"):
        promote(source, partition, packets, source_sha256=digest)
