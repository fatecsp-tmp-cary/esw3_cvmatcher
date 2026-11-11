"""Project the confirmed preview request into transient matching data."""

from src.schemas.candidate.curriculum import CurriculumRequest
from src.schemas.candidate.profile import (
    CandidateCompetency,
    CandidateProfile,
    CandidateProject,
    Education,
    Experience,
    Language,
)


def to_candidate_profile(curriculum: CurriculumRequest) -> CandidateProfile:
    """Preserve matching sections and dates without carrying the curriculum ID."""
    return CandidateProfile(
        skills=[item.descricao for item in curriculum.competencias],
        competencies=[
            CandidateCompetency(name=item.descricao, level=item.nivel)
            for item in curriculum.competencias
        ],
        job_titles=[item.cargo for item in curriculum.experiencias],
        experience=[
            Experience(
                title=item.cargo,
                company=item.empresa,
                description=item.descricao,
                start_date=item.inicio.isoformat(),
                end_date=item.fim.isoformat() if item.fim else None,
            )
            for item in curriculum.experiencias
        ],
        education=[
            Education(
                institution=item.instituicao,
                degree=item.curso,
                level=item.nivel,
                status=item.status,
                start_date=item.inicio.isoformat(),
                end_date=item.fim.isoformat() if item.fim else None,
            )
            for item in curriculum.formacoes
        ],
        academic_projects=[
            CandidateProject(
                title=item.titulo, technologies=item.tecnologias, description=item.descricao
            )
            for item in curriculum.projetos
        ],
        languages=[
            Language(name=item.idioma, proficiency=item.nivel) for item in curriculum.idiomas
        ],
    )
