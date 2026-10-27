"""Public ranked match response without persistence or lifecycle metadata."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.persistence.job.job import SeniorityLevel, WorkArrangement


class MatchedJob(BaseModel):
    """Descriptive canonical job fields exposed to API clients."""

    model_config = ConfigDict(extra="forbid")

    company: str | None = None
    title: str
    description: str | None = None
    keywords: list[str] | None = None
    location: dict[str, str | None] | None = None
    work_arrangement: WorkArrangement | None = None
    seniority_level: SeniorityLevel | None = None
    skills: list[str] | None = None
    salary: dict[str, int | float | str | None] | None = None
    currency: str | None = None
    job_url: str | None = None
    publication_date: datetime | None = None


class MatchResult(BaseModel):
    """One ranked job and its public compatibility/model metadata."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    job: MatchedJob
    score: float = Field(ge=0, le=100)
    embedding_model: str
    algorithm_version: str


class MatchesResponse(BaseModel):
    """Ranked recommendations in the matches array."""

    model_config = ConfigDict(extra="forbid")

    matches: list[MatchResult]
