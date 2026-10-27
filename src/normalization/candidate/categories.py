"""Map request-side category text onto canonical job enums."""

import unicodedata

from src.persistence.job.job import SeniorityLevel, WorkArrangement


def _key(value: str | None) -> str | None:
    if value is None:
        return None
    decomposed = unicodedata.normalize("NFKD", value.casefold().strip().rstrip("."))
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(unaccented.replace("-", " ").replace("_", " ").split()) or None


_SENIORITY_ALIASES = {
    "intern": SeniorityLevel.INTERN,
    "internship": SeniorityLevel.INTERN,
    "estagio": SeniorityLevel.INTERN,
    "junior": SeniorityLevel.JUNIOR,
    "jr": SeniorityLevel.JUNIOR,
    "mid": SeniorityLevel.MID,
    "middle": SeniorityLevel.MID,
    "mid level": SeniorityLevel.MID,
    "pleno": SeniorityLevel.MID,
    "senior": SeniorityLevel.SENIOR,
    "sr": SeniorityLevel.SENIOR,
    "specialist": SeniorityLevel.SPECIALIST,
    "especialista": SeniorityLevel.SPECIALIST,
    "coordinator": SeniorityLevel.COORDINATOR,
    "coordenador": SeniorityLevel.COORDINATOR,
    "coordenadora": SeniorityLevel.COORDINATOR,
}

_WORK_ARRANGEMENT_ALIASES = {
    "remote": WorkArrangement.REMOTE,
    "remoto": WorkArrangement.REMOTE,
    "home office": WorkArrangement.REMOTE,
    "teletrabalho": WorkArrangement.REMOTE,
    "hybrid": WorkArrangement.HYBRID,
    "hibrido": WorkArrangement.HYBRID,
    "on site": WorkArrangement.ON_SITE,
    "onsite": WorkArrangement.ON_SITE,
    "presencial": WorkArrangement.ON_SITE,
}


def normalize_seniority(value: str | None) -> SeniorityLevel | None:
    """Return the canonical seniority or ``None`` for missing/unknown text."""
    key = _key(value)
    return _SENIORITY_ALIASES.get(key) if key is not None else None


def normalize_work_arrangement(value: str | None) -> WorkArrangement | None:
    """Return the canonical work arrangement or ``None`` if unknown."""
    key = _key(value)
    return _WORK_ARRANGEMENT_ALIASES.get(key) if key is not None else None
