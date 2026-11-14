"""Approved best-effort APiBR count attestation, not an atomic snapshot proof."""

from datetime import datetime

from src.ingestion.adapters import SourceError

POLICY_VERSION = "apibr-health-exact-distinct-count-v1-best-effort"


def health_signature(payload):
    try:
        body = payload["checks"]["dataset_issues_body"]
        details = body["details"]
        count = details["records"]
        updated = details["last_updated"]
        if (
            payload["status"] != "healthy"
            or body["status"] != "healthy"
            or type(count) is not int
            or count < 0
            or details["from_backup"] is not False
            or not isinstance(updated, str)
            or datetime.fromisoformat(updated.replace("Z", "+00:00")).tzinfo is None
        ):
            return None
        return {"records": count, "last_updated": updated, "from_backup": False}
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


class SnapshotAttestation:
    def __init__(self, client):
        self.client = client
        self.before = None
        self.identities = set()
        self.rows = 0
        self.duplicates = 0
        self.invalid_ids = 0
        self.health_failed = False

    def health(self):
        fetch = getattr(self.client, "fetch_health", None)
        try:
            signature = health_signature(fetch()) if callable(fetch) else None
        except SourceError:
            # Exhausted transport failures retain ADR-003 rollback semantics.
            raise
        except Exception:
            signature = None
        if signature is None:
            self.health_failed = True
        return signature

    def begin(self):
        if hasattr(self.client, "request_failures"):
            self.client.request_failures = 0
        self.before = self.health()

    def observe(self, record):
        self.rows += 1
        identity = record.get("id") if isinstance(record, dict) else None
        if type(identity) not in (int, str) or not str(identity).strip():
            self.invalid_ids += 1
            return
        identity = str(identity).strip()
        if identity in self.identities:
            self.duplicates += 1
        self.identities.add(identity)

    def finish(self, *, rejections, terminal_empty):
        after = self.health()
        failures = getattr(self.client, "request_failures", None)
        complete = bool(
            terminal_empty
            and not rejections
            and not self.invalid_ids
            and not self.duplicates
            and type(failures) is int
            and failures == 0
            and not self.health_failed
            and self.before is not None
            and self.before == after
            and len(self.identities) == self.before["records"]
        )
        return {
            "policy": POLICY_VERSION,
            "before": self.before,
            "after": after,
            "rows": self.rows,
            "distinct_ids": len(self.identities),
            "duplicates": self.duplicates,
            "invalid_ids": self.invalid_ids,
            "rejections": rejections,
            "request_failures": failures,
            "health_failed": self.health_failed,
            "terminal_empty": terminal_empty,
            "qualified": complete,
        }
