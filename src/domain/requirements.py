"""Explicit requirement mappings and score-only comparison of known evidence."""

import re
import unicodedata

from src.domain.categories import normalize_seniority
from src.domain.job import SeniorityLevel

VERSION = "explicit-cefr-employment-equal-available-v2"
CEFR = ("A1", "A2", "B1", "B2", "C1", "C2")
LANGUAGES = {
    "portugues": "pt",
    "portuguese": "pt",
    "pt": "pt",
    "ingles": "en",
    "english": "en",
    "en": "en",
    "espanhol": "es",
    "spanish": "es",
    "es": "es",
    "frances": "fr",
    "french": "fr",
    "fr": "fr",
    "alemao": "de",
    "german": "de",
    "de": "de",
}
EMPLOYMENT = {
    "clt": "CLT",
    "carteira assinada": "CLT",
    "pj": "PJ",
    "pessoa juridica": "PJ",
    "estagio": "INTERNSHIP",
    "internship": "INTERNSHIP",
    "aprendiz": "APPRENTICESHIP",
    "apprenticeship": "APPRENTICESHIP",
    "temporario": "TEMPORARY",
    "temporary": "TEMPORARY",
    "freelance": "FREELANCE",
    "freelancer": "FREELANCE",
}


def key(value: str) -> str:
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(c)
        ).split()
    )


def cefr(value: str) -> str | None:
    match = re.fullmatch(r"(?:cefr\s*)?([abc][12])", key(value))
    return match[1].upper() if match else None


def language(value: str) -> str | None:
    return LANGUAGES.get(key(value))


def employment(value: str) -> str | None:
    # Full-time/contractor alone do not establish a Brazilian legal category.
    return EMPLOYMENT.get(key(value))


def explicit_seniority(title: str) -> SeniorityLevel | None:
    values = {normalize_seniority(word) for word in re.findall(r"[\w-]+", title)} - {None}
    return next(iter(values)) if len(values) == 1 else None


def comparable_score(
    candidate,
    job,
    *,
    skills: set[str],
    matched: set[str],
    requirements: list[str],
    relevant_experience=(),
    candidate_skills: set[str] | None = None,
) -> float:
    """Equal weights across comparable dimensions; unknown values are omitted.

    No employment preference exists in the public curriculum, so employment
    remains unscored. Experience and education are the existing semantic evidence.
    This function never filters candidates or uses location/work arrangement.
    """
    dimensions = []
    if candidate_skills is None:
        candidate_skills = matched
    if skills and candidate_skills:
        dimensions.append(100.0 * len(matched & skills) / len(skills))
    candidate_levels = {
        level
        for entry in relevant_experience
        if (level := explicit_seniority(entry.title)) is not None
    }
    required_level = job.seniority_level or explicit_seniority(job.title)
    if candidate_levels and required_level is not None:
        order = [
            SeniorityLevel.INTERN,
            SeniorityLevel.JUNIOR,
            SeniorityLevel.MID,
            SeniorityLevel.SENIOR,
        ]
        if required_level in candidate_levels:
            dimensions.append(100.0)
        elif required_level in order and any(value in order for value in candidate_levels):
            compatible = any(
                value in order and order.index(value) >= order.index(required_level)
                for value in candidate_levels
            )
            dimensions.append(100.0 if compatible else 0.0)
        # Specialist/coordinator are not inferred to be above/below other tracks.
    levels: dict[str, set[str]] = {}
    for entry in candidate.languages:
        name, proficiency = language(entry.name), cefr(entry.level)
        if name and proficiency:
            levels.setdefault(name, set()).add(proficiency)
    compared = []
    for text in requirements:
        # Accept only a complete explicit language/CEFR clause, never an arbitrary
        # nearby number or a guessed mapping from 'fluent'/'intermediate'.
        match = re.fullmatch(r"([\w ]+?)\s*[:=-]?\s*([abc][12])", key(text))
        if not match:
            continue
        name = language(match[1])
        required = match[2].upper()
        known = levels.get(name, set()) if name is not None else set()
        if len(known) == 1:
            compared.append(100.0 if CEFR.index(next(iter(known))) >= CEFR.index(required) else 0.0)
    if compared:
        dimensions.append(sum(compared) / len(compared))
    return sum(dimensions) / len(dimensions) if dimensions else 0.0
