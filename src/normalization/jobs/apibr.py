import re
import unicodedata
from datetime import UTC, datetime
from html import escape
from html.parser import HTMLParser
from typing import Any

from src.domain.categories import normalize_seniority, normalize_work_arrangement
from src.extraction.taxonomy import canonical_skill

# Aggregated repositories decorate labels with leading symbols ("🏢 Remoto") or
# explicit "Level-"/"Lang-" prefixes ("Level-sênior", "Lang-python").
_LABEL_DECORATION = re.compile(r"^[^\w.#+]+")
_LABEL_PREFIX = re.compile(r"^(?:level|lang)[-_ ]+", re.IGNORECASE)


class _HTMLTextParser(HTMLParser):
    _BLOCK_TAGS = {
        "br",
        "div",
        "li",
        "p",
        "section",
        "tr",
        "td",
        "th",
        "ul",
        "ol",
        "table",
        "blockquote",
        "pre",
        "hr",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def normalize_text(text: str | None, *, preserve_sections: bool = False) -> str | None:
    """Normalize Unicode composition and whitespace while preserving display text."""
    if not isinstance(text, str) or not text.strip():
        return None
    # Unknown angle-bracket constructs are literal Markdown/plain text, such
    # as autolinks and generic types. Escape before HTMLParser can discard them.
    html_tags = _HTMLTextParser._BLOCK_TAGS | {
        "a",
        "abbr",
        "b",
        "body",
        "caption",
        "cite",
        "code",
        "dd",
        "del",
        "dl",
        "dt",
        "em",
        "figure",
        "figcaption",
        "head",
        "html",
        "i",
        "img",
        "input",
        "ins",
        "label",
        "mark",
        "script",
        "small",
        "span",
        "strong",
        "style",
        "sub",
        "sup",
        "tbody",
        "thead",
        "title",
        "u",
        "s",
        "wbr",
    }
    text = re.sub(
        r"</?([A-Za-z][A-Za-z0-9:-]*)[^<>]*>",
        lambda match: match[0] if match[1].casefold() in html_tags else escape(match[0]),
        text,
    )
    parser = _HTMLTextParser()
    parser.feed(text)
    parser.close()
    normalized = unicodedata.normalize("NFC", "".join(parser.parts))
    if preserve_sections:
        return (
            "\n".join(" ".join(line.split()) for line in normalized.splitlines() if line.strip())
            or None
        )
    return " ".join(normalized.split()) or None


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


def vacancy_labels(raw_job: dict[str, Any]) -> list[str]:
    """Return cleaned vacancy-level label names from an APiBR issue.

    APiBR label objects carry a ``type``. Repository ``topic`` labels describe
    the aggregated repository, not the vacancy, and are ignored. Untyped string
    labels and the title-derived ``keywords`` are vacancy-level evidence.
    """
    names = []
    for field in ("labels", "keywords"):
        values = raw_job.get(field)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, dict):
                if value.get("type") == "topic":
                    continue
                value = value.get("name")
            text = normalize_text(value) if isinstance(value, str) else None
            if text is None:
                continue
            cleaned = _LABEL_PREFIX.sub("", _LABEL_DECORATION.sub("", text)).strip()
            if cleaned:
                names.append(cleaned)
    return names


def _only(values: set[Any]) -> Any | None:
    """Return the single explicit value; missing or conflicting evidence is unknown."""
    return next(iter(values)) if len(values) == 1 else None


def _normalize_publication_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("APiBR issue has an invalid created_at timestamp")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (ValueError, OverflowError):
        raise ValueError("APiBR issue has an invalid created_at timestamp") from None


def normalize_apibr_job(raw_job: dict[str, Any]) -> dict[str, Any]:
    """Map a raw APiBR issue to the source-supplied canonical job fields."""
    if not isinstance(raw_job, dict):
        raise ValueError("APiBR issue payload must be an object")

    source_id = raw_job.get("id")
    if isinstance(source_id, bool) or not isinstance(source_id, (int, str)):
        raise ValueError("APiBR issue is missing its required id")
    normalized_source_id = str(source_id).strip()
    if not normalized_source_id:
        raise ValueError("APiBR issue is missing its required id")

    title = normalize_text(raw_job.get("title"))
    if title is None:
        raise ValueError("APiBR issue is missing its required title")

    job_url = raw_job.get("html_url") or raw_job.get("url")
    if job_url is not None and not isinstance(job_url, str):
        raise ValueError("APiBR issue has an invalid job URL")

    keywords = normalize_keywords(raw_job.get("labels") or raw_job.get("keywords"))

    # Only exact shared aliases are mapped. Free text is never interpreted, and
    # conflicting labels (for example every option of an issue form) stay unknown.
    labels = vacancy_labels(raw_job)
    seniority = {level for name in labels if (level := normalize_seniority(name)) is not None}
    arrangement = {
        mode for name in labels if (mode := normalize_work_arrangement(name)) is not None
    }
    skills = sorted(
        {skill for name in labels if (skill := canonical_skill(name)) is not None},
        key=str.casefold,
    )

    return {
        "platform": "apibr",
        "source_job_id": normalized_source_id,
        "source_expires_at": None,
        "company": None,
        "title": title,
        "description": normalize_text(raw_job.get("body"), preserve_sections=True),
        "keywords": keywords,
        "skills": skills,
        "location": None,
        "work_arrangement": _only(arrangement),
        "seniority_level": _only(seniority),
        "salary": None,
        "currency": None,
        "job_url": job_url,
        "publication_date": _normalize_publication_date(raw_job.get("created_at")),
        # APiBR publishes its listing as open vacancies, so presence in it is
        # open evidence (ADR-014). A record explicitly marked closed is no
        # longer an available job even if it remains present in the scan.
        "status": "EXPIRED" if raw_job.get("state") == "closed" else "ACTIVE",
        "last_verified_at": None,
        # The source payload is retained only when its terms permit it.
        "raw": None,
        # Generated after normalization by indexing and change detection.
        "embedding": None,
        "content_hash": None,
    }
