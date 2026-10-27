"""Standalone copies of the agreed consumer contract for the mock API.

The request follows Sistema Currículo's flat payload (#103). The response follows
the ranked ``matches`` contract (#40). Keep these models aligned with the public
API schemas when those are present on the main branch.
"""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _valid_completion_month(value: str) -> str:
    try:
        date.fromisoformat(f"{value}-01" if len(value) == 7 else f"{value}-01-01")
    except ValueError:
        raise ValueError("previsao_conclusao must be a valid year and month") from None
    return value


CompletionDate = Annotated[
    str,
    Field(pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$"),
    AfterValidator(_valid_completion_month),
]
CurriculumId = Annotated[
    str,
    Field(
        min_length=8,
        max_length=64,
        pattern=(
            r"^(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-"
            r"[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}|cur_[A-Za-z0-9]{4,60})$"
        ),
    ),
]


class _RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PersonalData(_RequestModel):
    cidade: str | None = Field(default=None, min_length=2, max_length=60)
    estado: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    modalidade_preferencial: Literal["presencial", "remoto", "hibrido", "indiferente"]


class AcademicFormation(_RequestModel):
    curso: str = Field(min_length=3, max_length=100)
    instituicao: str = Field(default="FATEC-SP", min_length=2, max_length=100)
    status: Literal["em_andamento", "concluido", "trancado"]
    previsao_conclusao: CompletionDate | None = None


class Competency(_RequestModel):
    nome: str = Field(min_length=1, max_length=50)
    nivel: Literal["basico", "intermediario", "avancado"]


class CurriculumLanguage(_RequestModel):
    idioma: str = Field(min_length=2, max_length=40)
    nivel: Literal["basico", "intermediario", "avancado", "fluente"]


class ProfessionalExperience(_RequestModel):
    cargo: str = Field(min_length=2, max_length=80)
    empresa: str = Field(min_length=2, max_length=80)
    descricao: str | None = Field(default=None, max_length=1000)


class AcademicProject(_RequestModel):
    titulo: str = Field(min_length=3, max_length=100)
    tecnologias: list[str] = Field(default_factory=list)
    descricao: str | None = Field(default=None, max_length=1000)


class CurriculumRequest(_RequestModel):
    """Flat Sistema Currículo request; correlation ID is accepted but never echoed."""

    curriculo_id: CurriculumId
    dados_pessoais: PersonalData
    formacao_academica: list[AcademicFormation] = Field(min_length=1)
    competencias: list[Competency] = Field(min_length=1)
    idiomas: list[CurriculumLanguage] = Field(default_factory=list)
    experiencias_profissionais: list[ProfessionalExperience] = Field(default_factory=list)
    projetos_academicos: list[AcademicProject] = Field(default_factory=list)


class _ResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MatchedJob(_ResponseModel):
    company: str | None = None
    title: str
    description: str | None = None
    keywords: list[str] | None = None
    location: dict[str, str | None] | None = None
    work_arrangement: Literal["REMOTE", "HYBRID", "ON_SITE"] | None = None
    seniority_level: (
        Literal["INTERN", "JUNIOR", "MID", "SENIOR", "SPECIALIST", "COORDINATOR"] | None
    ) = None
    skills: list[str] | None = None
    salary: dict[str, int | float | str | None] | None = None
    currency: str | None = None
    job_url: str | None = None
    publication_date: datetime | None = None


class MatchResult(_ResponseModel):
    rank: int = Field(ge=1)
    job: MatchedJob
    score: float = Field(ge=0, le=100)
    embedding_model: str
    algorithm_version: str


class MatchesResponse(_ResponseModel):
    matches: list[MatchResult]
