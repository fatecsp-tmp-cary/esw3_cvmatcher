def normalize_text(text: str | None) -> str | None:
    """Remove espaços extras no início/fim e normaliza espaços internos."""
    if not text or not text.strip():
        return None
    return " ".join(text.strip().split())


def normalize_apibr_job(raw_job: dict) -> dict:
    """
    Recebe um payload bruto da APIBR (GitHub Vagas)
    e devolve o dicionário no modelo canônico Job.
    """
    return {
        "platform": "apibr",
        "source_job_id": str(raw_job.get("id")) if raw_job.get("id") else None,
        "title": normalize_text(raw_job.get("title")),
        "job_url": raw_job.get("html_url") or raw_job.get("url"),
        "description": normalize_text(raw_job.get("body")),
        "publication_date": raw_job.get("created_at"),
    }