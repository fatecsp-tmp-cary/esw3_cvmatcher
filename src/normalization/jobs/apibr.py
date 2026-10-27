import unicodedata
from typing import Any


def normalize_text(text: str | None) -> str | None:
    """Normalize Unicode composition and whitespace while preserving display text."""
    if not text or not text.strip():
        return None
    normalized = unicodedata.normalize("NFC", text)
    return " ".join(normalized.split())


def normalize_keywords(labels: Any) -> list[str]:
    """Safely extract label/keyword names from the APIBR payload."""
    if not labels or not isinstance(labels, list):
        return []

    keywords = []
    for label in labels:
        name = label.get("name") if isinstance(label, dict) else label
        normalized_name = normalize_text(name) if isinstance(name, str) else None
        if normalized_name:
            keywords.append(normalized_name)
    return keywords


def normalize_apibr_job(raw_job: dict[str, Any]) -> dict[str, Any]:
    """Map a raw APiBR issue to the source-supplied canonical job fields."""
    source_id = raw_job.get("id")
    if source_id is None or not str(source_id).strip():
        raise ValueError("APiBR issue is missing its required id")

    title = normalize_text(raw_job.get("title"))
    if title is None:
        raise ValueError("APiBR issue is missing its required title")

    return {
        "platform": "apibr",
        "source_job_id": str(source_id),
        "source_expires_at": None,
        "company": None,
        "title": title,
        "description": normalize_text(raw_job.get("body")),
        "keywords": normalize_keywords(raw_job.get("labels") or raw_job.get("keywords")),
        "skills": [],
        "location": None,
        "work_arrangement": None,
        "seniority_level": None,
        "salary": None,
        "currency": None,
        "job_url": raw_job.get("html_url") or raw_job.get("url"),
        "publication_date": raw_job.get("created_at"),
        "status": "DISCOVERED",
        "last_verified_at": None,
        # The source payload is retained only when its terms permit it.
        "raw": None,
        # Generated after normalization by indexing and change detection.
        "embedding": None,
        "content_hash": None,
    }
