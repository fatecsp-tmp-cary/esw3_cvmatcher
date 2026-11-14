from copy import deepcopy
from types import SimpleNamespace

import pytest

from src.ingestion.completeness import SnapshotAttestation


def health(count=2):
    return {
        "status": "healthy",
        "checks": {
            "dataset_issues_body": {
                "status": "healthy",
                "details": {
                    "records": count,
                    "last_updated": "2026-11-12T08:29:29-03:00",
                    "from_backup": False,
                },
            }
        },
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "none",
        "duplicate",
        "extra",
        "drift",
        "backup",
        "rejected",
        "request_failure",
        "no_terminal",
        "invalid_id",
    ],
)
def test_only_exact_distinct_stable_healthy_error_free_scans_qualify(mutation):
    before = health()
    after = deepcopy(before)
    if mutation == "drift":
        after["checks"]["dataset_issues_body"]["details"]["last_updated"] = "2026-11-12T09:00:00Z"
    if mutation == "backup":
        after["checks"]["dataset_issues_body"]["details"]["from_backup"] = True
    receipts = iter([before, after])
    client = SimpleNamespace(fetch_health=lambda: next(receipts), request_failures=0)
    probe = SnapshotAttestation(client)
    probe.begin()
    for identity in [1, 1] if mutation == "duplicate" else [1, 2]:
        probe.observe({"id": identity})
    if mutation == "extra":
        probe.observe({"id": 3})
    if mutation == "invalid_id":
        probe.observe({"id": True})
    if mutation == "request_failure":
        client.request_failures = 1
    result = probe.finish(
        rejections=int(mutation == "rejected"), terminal_empty=mutation != "no_terminal"
    )
    assert result["qualified"] is (mutation == "none")
    assert "identities" not in result
    assert "body" not in result
