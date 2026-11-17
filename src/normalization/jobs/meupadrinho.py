"""Canonical normalization for MeuPadrinho job records."""

import re
from datetime import UTC, datetime
from typing import Any

from src.domain.categories import (
    _key,
    normalize_seniority,
    normalize_work_arrangement,
)
from src.domain.job import SeniorityLevel, WorkArrangement
from src.extraction.taxonomy import canonical_skill
from src.normalization.jobs.apibr import normalize_text

MEUPADRINHO_VAGA_URL_TEMPLATE = "https://meupadrinho.com.br/api/vagas/{nano_id}"

# Keep MeuPadrinho-only aliases local so shared APiBR/candidate scoring and hashes stay unchanged.
_MEUPADRINHO_SENIORITY_ALIASES = {
    "staff": SeniorityLevel.SPECIALIST,
    "techlead": SeniorityLevel.COORDINATOR,
    "tech lead": SeniorityLevel.COORDINATOR,
    "diretor": SeniorityLevel.COORDINATOR,
    "diretora": SeniorityLevel.COORDINATOR,
    "director": SeniorityLevel.COORDINATOR,
}

_MEUPADRINHO_WORK_ARRANGEMENT_ALIASES = {
    "presecial": WorkArrangement.ON_SITE,
}


def _normalize_meupadrinho_seniority(value: str | None) -> SeniorityLevel | None:
    if (shared := normalize_seniority(value)) is not None:
        return shared
    key = _key(value)
    return _MEUPADRINHO_SENIORITY_ALIASES.get(key) if key is not None else None


def _normalize_meupadrinho_work_arrangement(value: str | None) -> WorkArrangement | None:
    if (shared := normalize_work_arrangement(value)) is not None:
        return shared
    key = _key(value)
    return _MEUPADRINHO_WORK_ARRANGEMENT_ALIASES.get(key) if key is not None else None


_BRAZIL_STATES = {
    "AC",
    "AL",
    "AP",
    "AM",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PR",
    "PE",
    "PI",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
}

_SALARY_VALUE = r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*([kK])?"
_SALARY_FULL = re.compile(
    rf"^\s*{_SALARY_VALUE}(?:\s*(?:-|–|—|~|\ba\b|\bat[eé]\b)\s*{_SALARY_VALUE})?\s*$",
    re.I,
)


def _extract_payload(raw_job: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(raw_job, dict):
        raise ValueError("MeuPadrinho job payload must be an object")

    contents = raw_job.get("contents")
    if contents is not None:
        if not isinstance(contents, dict):
            raise ValueError("MeuPadrinho job contents must be an object")
        payload = contents
    else:
        payload = raw_job

    source_id = raw_job.get("nano_id")
    if source_id is None:
        source_id = payload.get("nano_id")
    if source_id is None:
        source_id = payload.get("id")

    if isinstance(source_id, bool) or not isinstance(source_id, (int, str)):
        raise ValueError("MeuPadrinho job is missing its required nano_id")
    normalized_id = str(source_id).strip()
    if not normalized_id or len(normalized_id) > 255:
        raise ValueError("MeuPadrinho job is missing its required nano_id")

    return normalized_id, payload


def _normalize_publication_date(value: Any) -> datetime | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise ValueError("MeuPadrinho job has an invalid horario_registro timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (ValueError, OverflowError):
        raise ValueError("MeuPadrinho job has an invalid horario_registro timestamp") from None


def normalize_meupadrinho_location(value: Any) -> dict[str, str | None] | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("MeuPadrinho job has an invalid local field")
    raw = normalize_text(value)
    if raw is None:
        return None
    if raw.casefold() in ("brasil", "brazil"):
        return {"city": None, "state": None, "country": "Brasil", "raw": raw}

    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if len(parts) == 2 and parts[1].upper() in _BRAZIL_STATES:
        return {"city": parts[0], "state": parts[1].upper(), "country": "Brasil", "raw": raw}
    if len(parts) == 2 and parts[1].casefold() in ("brasil", "brazil"):
        return {"city": parts[0], "state": None, "country": "Brasil", "raw": raw}
    if len(parts) == 3:
        return {"city": parts[0], "state": parts[1], "country": parts[2], "raw": raw}
    return {"city": None, "state": None, "country": None, "raw": raw}


def _parse_salary_number(token: str, suffix: str | None = None) -> int | float:
    cleaned = token.strip()
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    elif "." in cleaned:
        integer_part, fractional_part = cleaned.split(".", 1)
        if len(fractional_part) == 3 and integer_part.isdigit() and fractional_part.isdigit():
            cleaned = integer_part + fractional_part
    value = float(cleaned)
    if suffix and suffix.casefold() == "k":
        value *= 1000.0
    return int(value) if value.is_integer() else value


def normalize_meupadrinho_salary(
    value: Any,
) -> tuple[dict[str, int | float | str | None] | None, str | None]:
    if value is None:
        return None, None
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ValueError("MeuPadrinho job has an invalid salario field")
    if isinstance(value, (int, float)):
        if value <= 0:
            return None, None
        numeric: int | float = int(value) if float(value).is_integer() else float(value)
        return {"min": numeric, "max": numeric}, "BRL"

    text = normalize_text(value)
    if text is None:
        return None, None
    match = _SALARY_FULL.fullmatch(text)
    if match is None:
        return None, None
    first = _parse_salary_number(match.group(1), match.group(2))
    if match.group(3) is None:
        return ({"min": first, "max": first}, "BRL") if first > 0 else (None, None)
    second = _parse_salary_number(match.group(3), match.group(4))
    if first <= 0 or second <= 0:
        return None, None
    return {"min": min(first, second), "max": max(first, second)}, "BRL"


def normalize_meupadrinho_skills(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = value.split(";")
    elif isinstance(value, list):
        raw_items = []
        for entry in value:
            if isinstance(entry, dict):
                entry = entry.get("nome") or entry.get("name")
            if isinstance(entry, str):
                raw_items.extend(entry.split(";"))
    else:
        raise ValueError("MeuPadrinho job has an invalid requisitos_tecnicos field")

    by_key: dict[str, str] = {}
    for raw_item in raw_items:
        cleaned = normalize_text(raw_item)
        if not cleaned:
            continue
        mapped = canonical_skill(cleaned) or cleaned
        key = mapped.casefold()
        if key not in by_key:
            by_key[key] = mapped
    return sorted(by_key.values(), key=lambda item: (item.casefold(), item))


def _normalize_keywords(payload: dict[str, Any], skills: list[str]) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for field in ("cargo", "plataforma", "tipo_contrato", "nivel_vaga", "nivel", "forma_trabalho"):
        raw_value = payload.get(field)
        if isinstance(raw_value, str):
            cleaned = normalize_text(raw_value)
            if cleaned and cleaned.casefold() not in seen:
                seen.add(cleaned.casefold())
                keywords.append(cleaned)
    for skill in skills:
        if skill.casefold() not in seen:
            seen.add(skill.casefold())
            keywords.append(skill)
    return keywords


def _normalize_description(payload: dict[str, Any]) -> str | None:
    base = normalize_text(payload.get("descricao_vaga"), preserve_sections=True)
    desirable = normalize_text(payload.get("requisitos_desejaveis"), preserve_sections=True)
    if base and desirable:
        return f"{base}\nRequisitos desejáveis:\n{desirable}"
    if desirable:
        return f"Requisitos desejáveis:\n{desirable}"
    return base


def _normalize_job_url(payload: dict[str, Any], nano_id: str) -> str:
    for field in ("link_vaga", "link_vaga_publicado", "link_plataforma_publicado"):
        candidate = payload.get(field)
        if candidate is None:
            continue
        if not isinstance(candidate, str):
            raise ValueError(f"MeuPadrinho job has an invalid {field} URL")
        cleaned = candidate.strip()
        if cleaned:
            return cleaned
    return MEUPADRINHO_VAGA_URL_TEMPLATE.format(nano_id=nano_id)


def normalize_meupadrinho_job(raw_job: Any) -> dict[str, Any]:
    """Map a raw MeuPadrinho record to canonical source-supplied job fields."""
    nano_id, payload = _extract_payload(raw_job)

    title_raw = payload.get("titulo_vaga")
    if title_raw is not None and not isinstance(title_raw, str):
        raise ValueError("MeuPadrinho job has an invalid titulo_vaga")
    title = normalize_text(title_raw)
    if title is None or len(title) > 255:
        raise ValueError("MeuPadrinho job is missing its required titulo_vaga")

    company_raw = payload.get("nome_empresa")
    if company_raw is not None and not isinstance(company_raw, str):
        raise ValueError("MeuPadrinho job has an invalid nome_empresa")
    company = normalize_text(company_raw)
    if company is not None and len(company) > 255:
        raise ValueError("MeuPadrinho job has an invalid nome_empresa")

    arrangement_raw = payload.get("forma_trabalho")
    if arrangement_raw is not None and not isinstance(arrangement_raw, str):
        raise ValueError("MeuPadrinho job has an invalid forma_trabalho")
    arrangement = _normalize_meupadrinho_work_arrangement(arrangement_raw)

    nivel_vaga_raw = payload.get("nivel_vaga")
    if nivel_vaga_raw is not None and not isinstance(nivel_vaga_raw, str):
        raise ValueError("MeuPadrinho job has an invalid nivel_vaga")
    nivel_raw = payload.get("nivel")
    if nivel_raw is not None and not isinstance(nivel_raw, str):
        raise ValueError("MeuPadrinho job has an invalid nivel")
    seniority = _normalize_meupadrinho_seniority(
        nivel_vaga_raw
    ) or _normalize_meupadrinho_seniority(nivel_raw)

    skills = normalize_meupadrinho_skills(payload.get("requisitos_tecnicos"))
    keywords = _normalize_keywords(payload, skills)
    location = normalize_meupadrinho_location(payload.get("local"))
    salary, currency = normalize_meupadrinho_salary(payload.get("salario"))
    job_url = _normalize_job_url(payload, nano_id)
    publication_date = _normalize_publication_date(payload.get("horario_registro"))
    description = _normalize_description(payload)

    closed = payload.get("vaga_encerrada")
    if closed is not None and not isinstance(closed, bool):
        raise ValueError("MeuPadrinho job has an invalid vaga_encerrada flag")

    return {
        "platform": "meupadrinho",
        "source_job_id": nano_id,
        "source_expires_at": None,
        "company": company,
        "title": title,
        "description": description,
        "keywords": keywords,
        "skills": skills,
        "location": location,
        "work_arrangement": arrangement,
        "seniority_level": seniority,
        "salary": salary,
        "currency": currency,
        "job_url": job_url,
        "publication_date": publication_date,
        "status": "EXPIRED" if closed is True else "ACTIVE",
        "last_verified_at": None,
        "raw": None,
        "embedding": None,
        "content_hash": None,
    }
