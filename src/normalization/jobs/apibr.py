def normalize_text(text: str | None) -> str | None:
    """Remove extra leading/trailing whitespace and normalize internal spaces."""
    if not text or not text.strip():
        return None
    return " ".join(text.strip().split())


def normalize_keywords(labels) -> list[str]:
    """Safely extract label/keyword names from the APIBR payload."""
    if not labels or not isinstance(labels, list):
        return []

    keywords = []
    for label in labels:
        if isinstance(label, dict) and "name" in label:
            keywords.append(label["name"])
        elif isinstance(label, str):
            keywords.append(label)
    return keywords


def normalize_apibr_job(raw_job: dict) -> dict:
    """
    Receive raw APIBR (GitHub Vagas) payload and return
    a normalized dictionary aligned with the Task 19 job schema.
    """
    return {
        "platform": "apibr",
        "source_job_id": str(raw_job.get("id")) if raw_job.get("id") else None,
        "company": None,
        "title": normalize_text(raw_job.get("title")),
        "description": normalize_text(raw_job.get("body")),
        "location": None,
        "work_arrangement": None,
        "seniority_level": None,
        "skills": [],
        "keywords": normalize_keywords(raw_job.get("labels") or raw_job.get("keywords")),
        "salary": None,
        "job_url": raw_job.get("html_url") or raw_job.get("url"),
        "publication_date": raw_job.get("created_at"),
    }
