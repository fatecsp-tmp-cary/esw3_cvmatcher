"""Explicit requirement mappings and score-only comparison of known evidence."""

import math
import re
import unicodedata
from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any

from src.domain.categories import normalize_seniority
from src.domain.job import SeniorityLevel

VERSION = "symmetric-seniority-filter-v4"
SENIORITY_LADDER = {
    SeniorityLevel.INTERN: 0,
    SeniorityLevel.JUNIOR: 1,
    SeniorityLevel.MID: 2,
    SeniorityLevel.SENIOR: 3,
    SeniorityLevel.SPECIALIST: 4,
    SeniorityLevel.COORDINATOR: 4,
}
SENIORITY_MILD_GAP_SCORE = 40.0
SENIORITY_MILD_GAP_MULTIPLIER = 0.85
_DAYS_PER_MONTH = 30.4375
_LOW_TENURE_MONTHS = 12.0
_HIGH_TENURE_MONTHS = 60.0
REQUIRED_SKILL_WEIGHT = 1.0
PREFERRED_SKILL_WEIGHT = 0.4
NICE_TO_HAVE_SKILL_WEIGHT = 0.15
SPARSE_PRIOR = 0.5
SPARSE_PRIOR_STRENGTH = 2.5
SKILL_PRECISION_CAP = 15
SKILL_F_BETA = 1.5
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


def _experience_months(entries: Iterable[Any], reference_date: date) -> float:
    """Sum merged non-overlapping dated experience intervals in months."""
    intervals: list[tuple[date, date]] = []
    for entry in entries:
        start = getattr(entry, "start_date", None)
        if not isinstance(start, date):
            continue
        raw_end = getattr(entry, "end_date", None)
        end = raw_end if isinstance(raw_end, date) else reference_date
        if end >= start:
            intervals.append((start, end))
    if not intervals:
        return 0.0
    intervals.sort()
    merged_days = 0
    cur_start, cur_end = intervals[0]
    for start, end in intervals[1:]:
        if start <= cur_end:
            if end > cur_end:
                cur_end = end
        else:
            merged_days += (cur_end - cur_start).days
            cur_start, cur_end = start, end
    merged_days += (cur_end - cur_start).days
    return merged_days / _DAYS_PER_MONTH


def _tenure_seniority(
    experiences: tuple[Any, ...],
    relevant: tuple[Any, ...],
    reference_date: date,
) -> SeniorityLevel | None:
    if not experiences:
        return SeniorityLevel.JUNIOR
    relevant_dated = [e for e in relevant if isinstance(getattr(e, "start_date", None), date)]
    if relevant_dated and _experience_months(relevant_dated, reference_date) >= _HIGH_TENURE_MONTHS:
        return SeniorityLevel.SENIOR
    total_dated = [e for e in experiences if isinstance(getattr(e, "start_date", None), date)]
    if total_dated and _experience_months(total_dated, reference_date) < _LOW_TENURE_MONTHS:
        return SeniorityLevel.JUNIOR
    return None


def resolve_candidate_seniority(
    candidate: Any,
    relevant_experience: Iterable[Any] = (),
    *,
    as_of_date: date | None = None,
) -> SeniorityLevel | None:
    """Determine candidate seniority from relevant title markers and tenure.

    When relevant tenure reaches 60+ months, take ``max(explicit, SENIOR)`` so an
    early-career ``Junior`` title cannot permanently mask senior tenure.
    ``as_of_date`` defaults to the current UTC date; callers should pass one
    request-scoped UTC date for per-request determinism.
    """
    relevant = tuple(relevant_experience)
    experiences = tuple(getattr(candidate, "experience", ()) or ())
    reference = as_of_date or datetime.now(UTC).date()
    tenure_level = _tenure_seniority(experiences, relevant, reference)
    explicit = [
        level for entry in relevant if (level := explicit_seniority(entry.title)) is not None
    ]
    if explicit:
        explicit_max = max(explicit, key=SENIORITY_LADDER.__getitem__)
        if tenure_level is SeniorityLevel.SENIOR:
            return max(explicit_max, tenure_level, key=SENIORITY_LADDER.__getitem__)
        return explicit_max
    return tenure_level


def seniority_alignment(
    candidate_level: SeniorityLevel | None,
    required_level: SeniorityLevel | None,
) -> tuple[bool, float | None, float]:
    """Return (allowed, seniority_dimension_score, final_score_multiplier)."""
    if candidate_level is None or required_level is None:
        return True, None, 1.0
    gap = abs(SENIORITY_LADDER[candidate_level] - SENIORITY_LADDER[required_level])
    if gap >= 2:
        return False, 0.0, 0.0
    if gap == 1:
        return True, SENIORITY_MILD_GAP_SCORE, SENIORITY_MILD_GAP_MULTIPLIER
    return True, 100.0, 1.0


def mandatory_coverage_ratio(exact_required: set[str], exact_matched: set[str]) -> float | None:
    """Compute ADR-021 exact-evidence mandatory skill coverage (score-only).

    For N=1 or 2 required concepts, target is N; for N>=3, max(3, ceil(0.70*N)).
    Returns ``None`` when N=0.
    """
    total = len(exact_required)
    if total == 0:
        return None
    target = total if total <= 2 else max(3, math.ceil(0.70 * total))
    return min(1.0, len(exact_matched & exact_required) / target)


def bidirectional_skill_score(
    *,
    required_skills: set[str],
    preferred_skills: set[str],
    nice_to_have_skills: set[str],
    matched: set[str],
    candidate_core_skills: set[str],
    exact_required: set[str] | None = None,
    exact_matched: set[str] | None = None,
) -> float:
    """Bidirectional tiered skill score with ADR-021 coverage and sparse damping."""
    all_job_skills = required_skills | preferred_skills | nice_to_have_skills
    if not all_job_skills or not candidate_core_skills:
        return 0.0
    total_weight = (
        REQUIRED_SKILL_WEIGHT * len(required_skills)
        + PREFERRED_SKILL_WEIGHT * len(preferred_skills)
        + NICE_TO_HAVE_SKILL_WEIGHT * len(nice_to_have_skills)
    )
    if total_weight <= 0.0:
        return 0.0
    effective_matched = matched & candidate_core_skills
    matched_weight = (
        REQUIRED_SKILL_WEIGHT * len(effective_matched & required_skills)
        + PREFERRED_SKILL_WEIGHT * len(effective_matched & preferred_skills)
        + NICE_TO_HAVE_SKILL_WEIGHT * len(effective_matched & nice_to_have_skills)
    )
    weighted_cov = matched_weight / total_weight
    effective_exact = (
        effective_matched if exact_matched is None else (exact_matched & candidate_core_skills)
    )
    mandatory_cov = (
        mandatory_coverage_ratio(exact_required, effective_exact) if exact_required else None
    )
    raw_cov = (
        0.5 * weighted_cov + 0.5 * mandatory_cov if mandatory_cov is not None else weighted_cov
    )
    smoothed_cov = min(
        1.0,
        max(
            0.0,
            (raw_cov * total_weight + SPARSE_PRIOR * SPARSE_PRIOR_STRENGTH)
            / (total_weight + SPARSE_PRIOR_STRENGTH),
        ),
    )
    # Count only core-supported matches in the precision numerator and clamp <= 1.0.
    precision_denom = min(len(candidate_core_skills), SKILL_PRECISION_CAP)
    core_hits = len(matched & candidate_core_skills & all_job_skills)
    raw_precision = min(1.0, core_hits / precision_denom)
    if smoothed_cov <= 0.0 or raw_precision <= 0.0:
        return 0.0
    effective_precision = math.sqrt(raw_precision)
    beta_sq = SKILL_F_BETA * SKILL_F_BETA
    f_beta = (
        (1.0 + beta_sq)
        * smoothed_cov
        * effective_precision
        / (beta_sq * smoothed_cov + effective_precision)
    )
    return min(100.0, max(0.0, 100.0 * f_beta))


def comparable_score(
    candidate,
    job,
    *,
    skills: set[str],
    matched: set[str],
    requirements: list[str],
    relevant_experience=(),
    candidate_skills: set[str] | None = None,
    required_skills: set[str] | None = None,
    preferred_skills: set[str] | None = None,
    nice_to_have_skills: set[str] | None = None,
    exact_required: set[str] | None = None,
    exact_matched: set[str] | None = None,
    candidate_core_skills: set[str] | None = None,
    as_of_date: date | None = None,
) -> float:
    """Equal weights across comparable dimensions; unknown values are omitted.

    No employment preference exists in the public curriculum, so employment
    remains unscored. Experience and education are the existing semantic evidence.
    This function never filters candidates or uses location/work arrangement.
    """
    dimensions = []
    if candidate_skills is None:
        candidate_skills = matched
    core_skills = candidate_skills if candidate_core_skills is None else candidate_core_skills
    req_set = skills if required_skills is None else required_skills
    pref_set = (set() if preferred_skills is None else preferred_skills) - req_set
    opt_set = (set() if nice_to_have_skills is None else nice_to_have_skills) - req_set - pref_set
    all_skills = req_set | pref_set | opt_set
    if all_skills and core_skills:
        dimensions.append(
            bidirectional_skill_score(
                required_skills=req_set,
                preferred_skills=pref_set,
                nice_to_have_skills=opt_set,
                matched=matched,
                candidate_core_skills=core_skills,
                exact_required=exact_required,
                exact_matched=exact_matched,
            )
        )
    candidate_level = resolve_candidate_seniority(
        candidate, relevant_experience, as_of_date=as_of_date
    )
    required_level = job.seniority_level or explicit_seniority(job.title)
    _, seniority_score, _ = seniority_alignment(candidate_level, required_level)
    if seniority_score is not None:
        dimensions.append(seniority_score)
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
