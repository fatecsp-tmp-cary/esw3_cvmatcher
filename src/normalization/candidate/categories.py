"""Map request-side category text onto canonical job enums."""

from dataclasses import dataclass

from src.domain.categories import normalize_seniority, normalize_work_arrangement
from src.domain.job import SeniorityLevel, WorkArrangement
from src.schemas.candidate.profile import CandidateProfile, Language


@dataclass(frozen=True, slots=True)
class NormalizedCandidateCategories:
    """Canonical enum categories plus validated free-text candidate values."""

    seniority: SeniorityLevel | None
    modes: tuple[WorkArrangement, ...]
    languages: tuple[Language, ...]
    employment_types: tuple[str, ...]


def normalize_candidate_categories(
    candidate: CandidateProfile,
) -> NormalizedCandidateCategories:
    """Normalize enum-backed categories and preserve other validated values.

    Unknown seniority and work-mode values produce no category. Language
    proficiency and employment type remain schema-validated free text until
    the job domain defines matching canonical values for them.
    """
    modes = tuple(
        dict.fromkeys(
            normalized
            for mode in candidate.preferences.modes
            if (normalized := normalize_work_arrangement(mode)) is not None
        )
    )
    return NormalizedCandidateCategories(
        seniority=normalize_seniority(candidate.seniority),
        modes=modes,
        languages=tuple(candidate.languages),
        employment_types=tuple(candidate.preferences.employment_types),
    )
