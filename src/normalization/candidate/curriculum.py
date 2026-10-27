"""Adapt the Sistema Currículo wire payload to internal matching data."""

from src.schemas.candidate.curriculum import CurriculumRequest
from src.schemas.candidate.profile import (
    CandidateCompetency,
    CandidateLocation,
    CandidateProfile,
    CandidateProject,
    Education,
    Experience,
    Language,
    Preferences,
)


def to_candidate_profile(curriculum: CurriculumRequest) -> CandidateProfile:
    """Build transient matching data without carrying the correlation ID."""
    preference = curriculum.dados_pessoais.modalidade_preferencial
    modes = [] if preference == "indiferente" else [preference]
    personal_location = CandidateLocation(
        city=curriculum.dados_pessoais.cidade,
        state=curriculum.dados_pessoais.estado,
    )
    locations = [
        " - ".join(
            value
            for value in (personal_location.city, personal_location.state)
            if value is not None
        )
    ]
    locations = [location for location in locations if location]

    return CandidateProfile(
        skills=[item.nome for item in curriculum.competencias],
        competencies=[
            CandidateCompetency(name=item.nome, level=item.nivel)
            for item in curriculum.competencias
        ],
        job_titles=[item.cargo for item in curriculum.experiencias_profissionais],
        experience=[
            Experience(title=item.cargo, company=item.empresa, description=item.descricao)
            for item in curriculum.experiencias_profissionais
        ],
        education=[
            Education(
                institution=item.instituicao,
                degree=item.curso,
                status=item.status,
                expected_completion=item.previsao_conclusao,
            )
            for item in curriculum.formacao_academica
        ],
        academic_projects=[
            CandidateProject(
                title=item.titulo,
                technologies=item.tecnologias,
                description=item.descricao,
            )
            for item in curriculum.projetos_academicos
        ],
        languages=[Language(name=item.idioma, proficiency=item.nivel) for item in curriculum.idiomas],
        locations=locations,
        personal_location=personal_location,
        preferences=Preferences(modes=modes),
    )
