"""Canonical job categories without database or web-framework dependencies."""

from enum import StrEnum


class WorkArrangement(StrEnum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ON_SITE = "ON_SITE"


class SeniorityLevel(StrEnum):
    INTERN = "INTERN"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    SPECIALIST = "SPECIALIST"
    COORDINATOR = "COORDINATOR"
