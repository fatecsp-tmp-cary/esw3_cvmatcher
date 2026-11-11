"""Lossless matching projection of the frozen public curriculum contract.

This representation deliberately has no identifier, collection caps or invented
matching evidence. It must remain request-scoped and must never be logged.
"""

from dataclasses import dataclass
from datetime import date

from src.schemas.candidate.curriculum import CurriculumRequest


@dataclass(frozen=True, slots=True, repr=False)
class Experience:
    company: str
    title: str
    description: str
    start_date: date
    end_date: date | None


@dataclass(frozen=True, slots=True, repr=False)
class Education:
    institution: str
    course: str
    level: str
    status: str
    start_date: date
    end_date: date | None


@dataclass(frozen=True, slots=True, repr=False)
class Project:
    title: str
    description: str
    technologies: str


@dataclass(frozen=True, slots=True, repr=False)
class Competency:
    description: str
    level: str


@dataclass(frozen=True, slots=True, repr=False)
class Language:
    name: str
    level: str


@dataclass(frozen=True, slots=True, repr=False)
class NormalizedCandidate:
    experience: tuple[Experience, ...]
    education: tuple[Education, ...]
    projects: tuple[Project, ...]
    competencies: tuple[Competency, ...]
    languages: tuple[Language, ...]


def normalize_curriculum(request: CurriculumRequest) -> NormalizedCandidate:
    """Preserve validated text, order and evidence without retaining the UUID.

    Free-text proficiency and technology strings stay intact: this adapter does
    not infer taxonomy, skill tokens, seniority or eligibility from them.
    """
    return NormalizedCandidate(
        experience=tuple(
            Experience(x.empresa, x.cargo, x.descricao, x.inicio, x.fim)
            for x in request.experiencias
        ),
        education=tuple(
            Education(x.instituicao, x.curso, x.nivel, x.status, x.inicio, x.fim)
            for x in request.formacoes
        ),
        projects=tuple(Project(x.titulo, x.descricao, x.tecnologias) for x in request.projetos),
        competencies=tuple(Competency(x.descricao, x.nivel) for x in request.competencias),
        languages=tuple(Language(x.idioma, x.nivel) for x in request.idiomas),
    )
