import unicodedata
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any


class _HTMLTextParser(HTMLParser):
    _BLOCK_TAGS = {"br", "div", "li", "p", "section", "tr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def normalize_text(text: str | None) -> str | None:
    """Normalize Unicode composition and whitespace while preserving display text."""
    if not isinstance(text, str) or not text.strip():
        return None
    parser = _HTMLTextParser()
    parser.feed(text)
    parser.close()
    normalized = unicodedata.normalize("NFC", "".join(parser.parts))
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


def _normalize_publication_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("APiBR issue has an invalid created_at timestamp")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("APiBR issue has an invalid created_at timestamp") from None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_apibr_job(raw_job: dict[str, Any]) -> dict[str, Any]:
    """Map a raw APiBR issue to the source-supplied canonical job fields."""
    source_id = raw_job.get("id")
    if isinstance(source_id, bool) or not isinstance(source_id, (int, str)):
        raise ValueError("APiBR issue is missing its required id")
    normalized_source_id = str(source_id).strip()
    if not normalized_source_id:
        raise ValueError("APiBR issue is missing its required id")

    title = normalize_text(raw_job.get("title"))
    if title is None:
        raise ValueError("APiBR issue is missing its required title")

    return {
        "platform": "apibr",
        "source_job_id": normalized_source_id,
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
        "publication_date": _normalize_publication_date(raw_job.get("created_at")),
        "status": "DISCOVERED",
        "last_verified_at": None,
        # The source payload is retained only when its terms permit it.
        "raw": None,
        # Generated after normalization by indexing and change detection.
        "embedding": None,
        "content_hash": None,
    }
