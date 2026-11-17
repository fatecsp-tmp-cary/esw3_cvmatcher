"""Versioned compatibility policy; no evidence of employment probability."""

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SimilarityCalibration:
    """Explicit provisional affine calibration; reviewed evaluation is required.

    E5 cosine values are concentrated. These anchors are initial development
    settings, not measured quality thresholds or mandatory exclusion evidence.
    """

    version: str = "e5-affine-050-100-v1-provisional"
    zero: float = 0.5
    full: float = 1.0

    def __post_init__(self) -> None:
        if not self.version or not -1 <= self.zero < self.full <= 1:
            raise ValueError("Invalid versioned similarity anchors")

    def score(self, cosine: float) -> float:
        if not math.isfinite(cosine) or not -1.00001 <= cosine <= 1.00001:
            raise ValueError("Invalid cosine similarity")
        return max(0.0, min(100.0, 100 * (cosine - self.zero) / (self.full - self.zero)))


def dual_similarity(np: Any, core: Any, full: Any, core_weight: float) -> Any:
    """Combine job-core and full-job cosines without letting boilerplate hurt.

    ``max(core, w*core + (1-w)*full)``: a long description can only lift an
    entry whose detail also matches; it never drags a matching role/stack below
    its core similarity. Works elementwise on NumPy arrays (``np`` is injected so
    this module keeps no import-time NumPy dependency).
    """
    return np.maximum(core, core_weight * core + (1.0 - core_weight) * full)


@dataclass(frozen=True, slots=True)
class RankingPolicy:
    version: str = "compatibility-v2-dual-vector-provisional"
    textual: float = 0.45
    semantic: float = 0.35
    structured: float = 0.20
    retrieval_limit: int = 100
    # ADR-027: share of the job-core cosine in the dual-vector entry similarity.
    core_weight: float = 0.65

    def __post_init__(self) -> None:
        weights = (self.textual, self.semantic, self.structured)
        if (
            not self.version
            or any(not math.isfinite(w) or w < 0 for w in weights)
            or not math.isclose(sum(weights), 1.0)
            or type(self.retrieval_limit) is not int
            or self.retrieval_limit < 1
            or not math.isfinite(self.core_weight)
            or not 0.0 <= self.core_weight <= 1.0
        ):
            raise ValueError("Invalid ranking policy")

    def score(self, textual: float, semantic: float, structured: float) -> float:
        values = (textual, semantic, structured)
        if any(not math.isfinite(v) or not 0 <= v <= 100 for v in values):
            raise ValueError("Component scores must be finite in [0,100]")
        total = self.textual * textual + self.semantic * semantic + self.structured * structured
        # Accepted weights may sum to one within floating-point tolerance. Keep
        # their blend inside the public score bounds even at the upper endpoint.
        return min(100.0, max(0.0, total))
