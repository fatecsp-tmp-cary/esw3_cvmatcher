"""CandidateProfile: the structured CV data received by POST /matches.

The external parser supplies this JSON. It is request-scoped: never persist or log it.

Categorical values (seniority, proficiency, modes, employment types) arrive as free text;
mapping them to canonical values belongs to candidate normalization, not to this schema.
"""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Bounds keep a single request from carrying an unbounded amount of text.
ShortText = Annotated[str, Field(min_length=1, max_length=200)]
LongText = Annotated[str, Field(min_length=1, max_length=5000)]
# Year ("2021") or year-month ("2021-03"): CVs rarely state the day.
PartialDate = Annotated[str, Field(pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$", examples=["2021-03"])]


class _Schema(BaseModel):
    # Unknown fields are rejected so a drift in the parser output fails loudly.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _check_period(start: str | None, end: str | None) -> None:
    # Both values match PartialDate, so string order is chronological order.
    if start is not None and end is not None and end[: len(start)] < start[: len(end)]:
        raise ValueError("end_date must not be earlier than start_date")


class Experience(_Schema):
    title: ShortText
    company: ShortText | None = None
    description: LongText | None = None
    skills: list[ShortText] = Field(default_factory=list, max_length=100)
    start_date: PartialDate | None = None
    end_date: PartialDate | None = Field(default=None, description="Omitted for a current role.")

    @model_validator(mode="after")
    def _period_is_ordered(self) -> Self:
        _check_period(self.start_date, self.end_date)
        return self


class Education(_Schema):
    institution: ShortText | None = None
    degree: ShortText | None = Field(default=None, examples=["Bachelor"])
    field_of_study: ShortText | None = Field(default=None, examples=["Computer Science"])
    start_date: PartialDate | None = None
    end_date: PartialDate | None = None

    @model_validator(mode="after")
    def _has_content_and_ordered_period(self) -> Self:
        if self.institution is None and self.degree is None and self.field_of_study is None:
            raise ValueError("education needs institution, degree or field_of_study")
        _check_period(self.start_date, self.end_date)
        return self


class Certification(_Schema):
    name: ShortText
    issuer: ShortText | None = None


class Language(_Schema):
    name: ShortText = Field(examples=["English"])
    proficiency: ShortText | None = Field(default=None, examples=["advanced"])


class Preferences(_Schema):
    employment_types: list[ShortText] = Field(
        default_factory=list, max_length=10, examples=[["full-time"]]
    )
    modes: list[ShortText] = Field(default_factory=list, max_length=10, examples=[["remote"]])


class CandidateProfile(_Schema):
    """Structured CV data. At least one of skills, job_titles, occupations or experience."""

    skills: list[ShortText] = Field(default_factory=list, max_length=200)
    job_titles: list[ShortText] = Field(default_factory=list, max_length=50)
    occupations: list[ShortText] = Field(default_factory=list, max_length=50)
    experience: list[Experience] = Field(default_factory=list, max_length=50)
    education: list[Education] = Field(default_factory=list, max_length=20)
    certifications: list[Certification] = Field(default_factory=list, max_length=50)
    languages: list[Language] = Field(default_factory=list, max_length=20)
    locations: list[ShortText] = Field(
        default_factory=list,
        max_length=20,
        description="Kept as matching data; never used for geographic eligibility.",
    )
    seniority: ShortText | None = Field(default=None, examples=["senior"])
    years_experience: float | None = Field(default=None, ge=0, le=70)
    preferences: Preferences = Field(default_factory=Preferences)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "skills": ["Python", "PostgreSQL", "FastAPI"],
                    "job_titles": ["Backend Developer"],
                    "experience": [
                        {
                            "title": "Backend Developer",
                            "company": "Acme",
                            "skills": ["Python", "Docker"],
                            "start_date": "2021-03",
                        }
                    ],
                    "education": [
                        {"degree": "Technologist", "field_of_study": "Systems Development"}
                    ],
                    "languages": [{"name": "English", "proficiency": "advanced"}],
                    "seniority": "mid",
                    "years_experience": 4,
                    "preferences": {"modes": ["remote"]},
                }
            ]
        }
    )

    @model_validator(mode="after")
    def _has_matchable_content(self) -> Self:
        if not (self.skills or self.job_titles or self.occupations or self.experience):
            raise ValueError(
                "profile needs at least one of skills, job_titles, occupations or experience"
            )
        return self
