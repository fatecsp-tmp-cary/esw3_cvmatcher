"""Compatibility exports of the shared public API contract.

Both applications use the same models; the mock does not maintain schema copies.
"""

from src.schemas.candidate.curriculum import CurriculumRequest
from src.schemas.matches import MatchedJob, MatchesResponse, MatchResult

__all__ = ["CurriculumRequest", "MatchedJob", "MatchesResponse", "MatchResult"]
