"""Matching data from Sistema Currículo's implemented curriculum preview.

Field names follow the preview DTOs at source commit 66af300; validation follows
its domain models. Contact, identity and presentation data are outside matching.
"""

from datetime import date
from re import fullmatch
from typing import Annotated, Literal, Self
from unicodedata import category
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def _without_controls(value: object) -> object:
    """Reject control characters in education and project text, as the source does."""
    if isinstance(value, str) and any(category(character) == "Cc" for character in value):
        raise ValueError("text must not contain control characters")
    return value


NonemptyText = Annotated[str, Field(min_length=1)]
EducationText = Annotated[
    str, Field(min_length=1, max_length=200), BeforeValidator(_without_controls)
]
ProjectTitle = EducationText
ProjectDescription = Annotated[
    str, Field(min_length=1, max_length=2000), BeforeValidator(_without_controls)
]
ProjectTechnologies = Annotated[
    str, Field(min_length=1, max_length=300), BeforeValidator(_without_controls)
]


def _private_uuid(value: object) -> object:
    """Parse source UUID strings without reflecting parser input in errors."""
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            raise ValueError("identifier must be a valid UUID") from None
    return value


CurriculumId = Annotated[UUID, BeforeValidator(_private_uuid)]


class _CurriculumModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _calendar_date(value: object) -> object:
    if type(value) is date:
        return value
    if not isinstance(value, str) or fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("date must use YYYY-MM-DD")
    return value


CalendarDate = Annotated[date, BeforeValidator(_calendar_date)]


class _Period(_CurriculumModel):
    """A chronological period; null end means ongoing."""

    inicio: CalendarDate
    fim: CalendarDate | None

    @model_validator(mode="after")
    def _ordered_period(self) -> Self:
        if self.fim is not None and self.fim < self.inicio:
            raise ValueError("fim must not precede inicio")
        return self


class AcademicFormation(_Period):
    """Academic fields and vocabulary from the implemented formation model."""

    instituicao: EducationText
    curso: EducationText
    nivel: Literal[
        "ensino_fundamental",
        "ensino_medio",
        "tecnico",
        "tecnologo",
        "graduacao",
        "especializacao",
        "mestrado",
        "doutorado",
    ]
    status: Literal["em_andamento", "concluido", "interrompido"]

    @model_validator(mode="after")
    def _completed_formation_has_end(self) -> Self:
        if self.status == "concluido" and self.fim is None:
            raise ValueError("completed formation requires fim")
        return self


class Competency(_CurriculumModel):
    """Preview competency description and free-text proficiency."""

    descricao: NonemptyText
    nivel: NonemptyText


class CurriculumLanguage(_CurriculumModel):
    """Preview language name and free-text proficiency."""

    idioma: NonemptyText
    nivel: NonemptyText


class ProfessionalExperience(_Period):
    """Professional experience with the source's start and nullable end dates."""

    empresa: NonemptyText
    cargo: NonemptyText
    descricao: NonemptyText


class AcademicProject(_CurriculumModel):
    """Source project texts, including technologies as a single string."""

    titulo: ProjectTitle
    descricao: ProjectDescription
    tecnologias: ProjectTechnologies


class CurriculumRequest(_CurriculumModel):
    """Matching sections of the preview; the curriculum ID remains request-scoped."""

    curriculo_id: CurriculumId
    formacoes: list[AcademicFormation]
    experiencias: list[ProfessionalExperience]
    projetos: list[AcademicProject]
    competencias: list[Competency]
    idiomas: list[CurriculumLanguage]
