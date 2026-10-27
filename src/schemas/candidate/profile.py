"""Internal, request-scoped candidate representation used by matching.

The API accepts :class:`CurriculumRequest` from Sistema Currículo and adapts it
to this matching representation. Never persist or log candidate data.

Categorical values (seniority, proficiency, modes, employment types) arrive as free text;
mapping them to canonical values belongs to candidate normalization, not to this schema.
Their canonical values are defined once the job data is available (#83).
"""

from datetime import date
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

# Bounds keep a single request from carrying an unbounded amount of text.
ShortText = Annotated[str, Field(min_length=1, max_length=200)]
LongText = Annotated[str, Field(min_length=1, max_length=5000)]


def _is_calendar_day(value: str) -> str:
    if len(value) == len("YYYY-MM-DD"):
        try:
            date.fromisoformat(value)
        except ValueError:
            raise ValueError("date is not a valid calendar day") from None
    return value


# ISO 8601 at the precision the CV states: "2021", "2021-03" or "2021-03-15".
PartialDate = Annotated[
    str,
    Field(pattern=r"^\d{4}(-(0[1-9]|1[0-2])(-\d{2})?)?$", examples=["2021-03"]),
    AfterValidator(_is_calendar_day),
]


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
    description: str | None = Field(default=None, max_length=1000)
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
    status: ShortText | None = None
    start_date: PartialDate | None = None
    end_date: PartialDate | None = None
    expected_completion: PartialDate | None = None

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


class CandidateCompetency(_Schema):
    name: ShortText
    level: ShortText


class CandidateProject(_Schema):
    title: ShortText
    technologies: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=1000)


class CandidateLocation(_Schema):
    city: ShortText | None = None
    state: ShortText | None = None


class Preferences(_Schema):
    employment_types: list[ShortText] = Field(
        default_factory=list, max_length=10, examples=[["full-time"]]
    )
    modes: list[ShortText] = Field(default_factory=list, max_length=10, examples=[["remote"]])


class CandidateProfile(_Schema):
    """Transient matching fields adapted from a complete curriculum request."""

    skills: list[ShortText] = Field(min_length=1)
    competencies: list[CandidateCompetency] = Field(default_factory=list)
    job_titles: list[ShortText] = Field(default_factory=list)
    occupations: list[ShortText] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    academic_projects: list[CandidateProject] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    locations: list[ShortText] = Field(
        default_factory=list,
        description="Kept as matching data; never used for geographic eligibility.",
    )
    personal_location: CandidateLocation | None = None
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
    def _has_role_context(self) -> Self:
        if not (self.job_titles or self.experience or self.education or self.academic_projects):
            raise ValueError("profile needs role, education or project context")
        return self
