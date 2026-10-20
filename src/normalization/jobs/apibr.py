def normalize_text(text: str | None) -> str | None:
    """Remove espaços extras no início/fim e normaliza espaços internos."""
    if not text or not text.strip():
        return None
    return " ".join(text.strip().split())


def normalize_keywords(labels) -> list[str]:
    """Extrai os nomes das labels/keywords da APIBR de forma segura."""
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
    Recebe um payload bruto da APIBR (GitHub Vagas)
    e devolve o dicionário completo alinhado com o modelo Job da Task 19.
    """
    return {
        "platform": "apibr",
        "source_job_id": str(raw_job.get("id")) if raw_job.get("id") else None,
        "company": None,
        "title": normalize_text(raw_job.get("title")),
        "description": normalize_text(raw_job.get("body")),
        "location": None,  # Armazenado em JSON conforme especificação
        "work_arrangement": None,
        "seniority_level": None,
        "skills": [],  # Armazena habilidades normalizadas
        "keywords": normalize_keywords(
            raw_job.get("labels") or raw_job.get("keywords")
        ),  # Preserva as tags e labels
        "salary": None,  # Armazenado em JSON conforme especificação
        "job_url": raw_job.get("html_url") or raw_job.get("url"),
        "publication_date": raw_job.get("created_at"),
    }
