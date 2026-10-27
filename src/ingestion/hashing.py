"""Deterministic hashes of normalized job content."""

import hashlib
import json
from datetime import datetime
from typing import Any

HASH_FIELDS = (
    "source_expires_at",
    "company",
    "title",
    "description",
    "keywords",
    "skills",
    "location",
    "work_arrangement",
    "seniority_level",
    "salary",
    "currency",
    "job_url",
    "publication_date",
)


def content_hash(job: dict[str, Any]) -> str:
    """Hash normalized descriptive fields, excluding lifecycle and persistence data."""
    content = {field: job.get(field) for field in HASH_FIELDS}
    encoded = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda value: value.isoformat() if isinstance(value, datetime) else str(value),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
