"""Sistema Currículo's complete request body for POST /matches."""

from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _valid_completion_month(value: str) -> str:
    try:
        date.fromisoformat(f"{value}-01-01" if len(value) == 4 else f"{value}-01")
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


class _CurriculumModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PersonalData(_CurriculumModel):
    cidade: str | None = Field(default=None, min_length=2, max_length=60)
    estado: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    modalidade_preferencial: Literal["presencial", "remoto", "hibrido", "indiferente"]


class AcademicFormation(_CurriculumModel):
    curso: str = Field(min_length=3, max_length=100)
    instituicao: str = Field(default="FATEC-SP", min_length=2, max_length=100)
    status: Literal["em_andamento", "concluido", "trancado"]
    previsao_conclusao: CompletionDate | None = None


class Competency(_CurriculumModel):
    nome: str = Field(min_length=1, max_length=50)
    nivel: Literal["basico", "intermediario", "avancado"]


class CurriculumLanguage(_CurriculumModel):
    idioma: str = Field(min_length=2, max_length=40)
    nivel: Literal["basico", "intermediario", "avancado", "fluente"]


class ProfessionalExperience(_CurriculumModel):
    cargo: str = Field(min_length=2, max_length=80)
    empresa: str = Field(min_length=2, max_length=80)
    descricao: str | None = Field(default=None, max_length=1000)


class AcademicProject(_CurriculumModel):
    titulo: str = Field(min_length=3, max_length=100)
    tecnologias: list[str] = Field(default_factory=list)
    descricao: str | None = Field(default=None, max_length=1000)


class CurriculumRequest(_CurriculumModel):
    """Flat curriculum payload; the ID is opaque and transient."""

    curriculo_id: CurriculumId
    dados_pessoais: PersonalData
    formacao_academica: list[AcademicFormation] = Field(min_length=1)
    competencias: list[Competency] = Field(min_length=1)
    idiomas: list[CurriculumLanguage] = Field(default_factory=list)
    experiencias_profissionais: list[ProfessionalExperience] = Field(default_factory=list)
    projetos_academicos: list[AcademicProject] = Field(default_factory=list)
