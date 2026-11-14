import pytest

from src.domain.job import SeniorityLevel, WorkArrangement
from src.normalization.jobs.apibr import normalize_apibr_job, section_values

ARRANGEMENT = ("Aloca[cç][aã]o", "Modalidade", "Local(?:iza[cç][aã]o)?")
SENIORITY = ("N[ií]vel", "Senioridade")


def job(title="Developer", labels=None, body=None):
    return normalize_apibr_job({"id": 1, "title": title, "labels": labels or [], "body": body})


@pytest.mark.parametrize(
    ("names", "body", "expected"),
    [
        (SENIORITY, "- 📈 Nível: pleno", ["pleno"]),
        (SENIORITY, "**Nível:** Sênior", ["Sênior"]),
        (SENIORITY, "## Nível\n- Júnior", ["Júnior"]),
        (
            ARRANGEMENT,
            "### Alocação\n- [ ] Alocado\n- [x] Remoto\n- [ ] Híbrido\n### Nível",
            ["Remoto"],
        ),
        (ARRANGEMENT, "### Alocação\n- [X] Híbrido\n- [x] Remoto", ["Híbrido", "Remoto"]),
        (ARRANGEMENT, "Local:\nRemoto\nBenefícios: plano de saúde", ["Remoto"]),
        # Prose, other fields that merely start with the name, and unrelated sections.
        (SENIORITY, "Nível de inglês: avançado", []),
        (SENIORITY, "Vaga remota para pessoa sênior.", []),
        (ARRANGEMENT, "## Benefícios\n- Remoto", []),
        (ARRANGEMENT, "", []),
        (ARRANGEMENT, None, []),
    ],
)
def test_section_values_read_only_explicit_fields(names, body, expected):
    assert section_values(body, names) == expected


def test_inline_body_fields_fill_both_categories():
    result = job(body="- 📍 Localização: Remoto\n- 📈 Nível: pleno\n- 📃 Contrato: clt")

    assert result["seniority_level"] == SeniorityLevel.MID
    assert result["work_arrangement"] == WorkArrangement.REMOTE


def test_checked_form_options_resolve_arrangement_but_not_conflicting_levels():
    body = (
        "### Alocação\n- [ ] Alocado\n- [x] Remoto\n- [ ] Presencial\n"
        "### Nível\n- [ ] Júnior\n- [x] Sênior\n- [x] Especialista"
    )
    labels = ["Remoto", "Presencial", "Híbrido", "Júnior", "Pleno", "Sênior", "Especialista"]

    result = job(title="[Remoto] Senior Developer", labels=labels, body=body)

    assert result["work_arrangement"] == WorkArrangement.REMOTE
    # Explicit evidence exists but conflicts: the title must not break the tie.
    assert result["seniority_level"] is None


def test_labels_take_precedence_over_body_sections_and_title():
    result = job(
        title="[Presencial] Senior Developer",
        labels=["Pleno", "Remoto"],
        body="Nível: sênior\nLocalização: Híbrido",
    )

    assert result["seniority_level"] == SeniorityLevel.MID
    assert result["work_arrangement"] == WorkArrangement.REMOTE


def test_body_section_is_used_when_labels_have_no_value():
    result = job(labels=["Java"], body="Nível: sênior")

    assert result["seniority_level"] == SeniorityLevel.SENIOR


@pytest.mark.parametrize(
    ("title", "seniority", "arrangement"),
    [
        ("[Remoto] Desenvolvedor Python", None, WorkArrangement.REMOTE),
        ("[ITAÚ] [JAVA] [AWS] [100% REMOTO]", None, WorkArrangement.REMOTE),
        ("Senior Backend Engineer", SeniorityLevel.SENIOR, None),
        (
            "[Developer SENIOR NodeJS, Python, Dart, or Go] Remote - Need to speak ENGLISH",
            SeniorityLevel.SENIOR,
            WorkArrangement.REMOTE,
        ),
        ("Estágio em Desenvolvimento - Híbrido", SeniorityLevel.INTERN, WorkArrangement.HYBRID),
        # More than one distinct value in the title is ambiguous.
        ("Desenvolvedor Pleno/Sênior [Remoto ou Presencial]", None, None),
        ("Júnior ou Pleno", None, None),
        # A dotted name is one token, not the word it starts with.
        ("Software Engineer at Remote.com", None, None),
        ("Engineer (Remote-first company)", None, None),
        ("Desenvolvedor Java", None, None),
    ],
)
def test_a_single_recognizable_title_word_is_used_when_nothing_explicit_exists(
    title, seniority, arrangement
):
    result = job(title=title)

    assert result["seniority_level"] == seniority
    assert result["work_arrangement"] == arrangement


def test_title_word_is_ignored_when_explicit_evidence_conflicts():
    result = job(title="[Remoto] Developer", labels=["Remoto", "Presencial"])

    assert result["work_arrangement"] is None


def test_unrecognized_explicit_evidence_does_not_block_the_title():
    # "Alocado" has no canonical arrangement, so it is not evidence at all.
    result = job(title="[Híbrido] Developer", labels=["Alocado"])

    assert result["work_arrangement"] == WorkArrangement.HYBRID


def test_enrichment_does_not_change_skills_company_location_or_salary():
    result = job(
        title="[Remoto] Senior Python Developer",
        body="Nível: sênior\nSalário: R$ 8.000,00\nLocalização: Remoto",
    )

    assert result["skills"] == []
    assert result["company"] is None
    assert result["location"] is None
    assert result["salary"] is None
