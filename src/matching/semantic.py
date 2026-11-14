"""Aggregate calibrated per-entry scores; inference and calibration are separate.

No candidate data, per-entry embeddings or evidence are persisted here.
"""

from dataclasses import dataclass
from datetime import date
from math import isfinite


@dataclass(frozen=True, slots=True, repr=False)
class ExperienceScore:
    score: float
    start_date: date
    end_date: date | None

    def __post_init__(self) -> None:
        _validate_score(self.score)
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("experience dates must be ordered")

    @property
    def recency(self) -> tuple[bool, date, date]:
        return self.end_date is None, self.end_date or date.min, self.start_date


def _validate_score(value: float) -> None:
    if not isfinite(value) or not 0 <= value <= 100:
        raise ValueError("calibrated entry score must be finite and within [0,100]")


@dataclass(frozen=True, slots=True)
class SemanticPolicy:
    """Interview starting coefficients; calibration/release approval is pending."""

    version: str = "semantic-aggregation-v2-provisional"
    experience_weight: float = 0.8
    education_weight: float = 0.2
    recency_weights: tuple[float, float, float] = (1.5, 1.25, 1.0)

    def __post_init__(self) -> None:
        weights = (self.experience_weight, self.education_weight, *self.recency_weights)
        if not self.version.strip() or any(not isfinite(x) or x <= 0 for x in weights):
            raise ValueError("version and finite positive weights are required")
        if len(self.recency_weights) != 3 or not (
            self.recency_weights[0] > self.recency_weights[1] > self.recency_weights[2]
        ):
            raise ValueError("three strictly descending recency weights are required")


_DEFAULT_POLICY = SemanticPolicy()


def selected_experience_indices(experiences: tuple[ExperienceScore, ...]) -> tuple[int, ...]:
    """Share the fixed relevance/recency/input-position selection with supporting scoring."""
    return tuple(
        sorted(
            range(len(experiences)),
            key=lambda index: (experiences[index].score, experiences[index].recency),
            reverse=True,
        )[:3]
    )


def semantic_score(
    experiences: tuple[ExperienceScore, ...],
    education_scores: tuple[float, ...],
    policy: SemanticPolicy = _DEFAULT_POLICY,
) -> float:
    """Select by relevance, then weight by recency and blend available sections.

    Inputs are already evaluated against one job and calibrated to [0,100].
    Equal similarity sorts by recency, then original input position. Recency
    groups receive weights 1.5/1.25/1.0 from newest to oldest; tied dates share a
    group. With fewer distinct groups, use the first one/two weights.
    """
    for score in education_scores:
        _validate_score(score)
    # Stable sorting preserves input position when both score and recency tie.
    selected = [experiences[index] for index in selected_experience_indices(experiences)]
    total = denominator = 0.0
    # Scale only available sections. An absent section's much larger weight
    # must not underflow the sole available component to zero.
    available_weights = []
    if selected:
        available_weights.append(policy.experience_weight)
    if education_scores:
        available_weights.append(policy.education_weight)
    scale = max(available_weights, default=1.0)
    experience_weight = policy.experience_weight / scale if selected else 0.0
    education_weight = policy.education_weight / scale if education_scores else 0.0
    if selected:
        recencies = sorted({x.recency for x in selected}, reverse=True)
        weights = {
            recency: policy.recency_weights[i] / policy.recency_weights[0]
            for i, recency in enumerate(recencies)
        }
        weight_sum = sum(weights[x.recency] for x in selected)
        experience = sum(x.score * weights[x.recency] for x in selected) / weight_sum
        total += experience_weight * experience
        denominator += experience_weight
    if education_scores:
        total += education_weight * max(education_scores)
        denominator += education_weight
    return min(100.0, max(0.0, total / denominator)) if denominator else 0.0
