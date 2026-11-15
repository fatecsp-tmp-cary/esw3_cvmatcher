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


def test_title_wins_over_checked_options_and_conflicting_labels():
    body = (
        "### Alocação\n- [ ] Alocado\n- [x] Remoto\n- [ ] Presencial\n"
        "### Nível\n- [ ] Júnior\n- [x] Sênior\n- [x] Especialista"
    )
    labels = ["Remoto", "Presencial", "Híbrido", "Júnior", "Pleno", "Sênior", "Especialista"]

    result = job(title="[Remoto] Senior Developer", labels=labels, body=body)

    assert result["work_arrangement"] == WorkArrangement.REMOTE
    assert result["seniority_level"] == SeniorityLevel.SENIOR


def test_title_takes_precedence_over_labels_and_body_sections():
    result = job(
        title="[Presencial] Senior Developer",
        labels=["Pleno", "Remoto"],
        body="Nível: sênior\nLocalização: Híbrido",
    )

    assert result["seniority_level"] == SeniorityLevel.SENIOR
    assert result["work_arrangement"] == WorkArrangement.ON_SITE


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
        # Multiple title values use the accepted restrictive ordering.
        (
            "Desenvolvedor Pleno/Sênior [Remoto ou Presencial]",
            SeniorityLevel.SENIOR,
            WorkArrangement.ON_SITE,
        ),
        ("Júnior ou Pleno", SeniorityLevel.MID, None),
        # A dotted name is one token, not the word it starts with.
        ("Software Engineer at Remote.com", None, None),
        ("Engineer (Remote-first company)", None, None),
        ("Desenvolvedor Java", None, None),
    ],
)
def test_title_words_resolve_by_the_accepted_order(title, seniority, arrangement):
    result = job(title=title)

    assert result["seniority_level"] == seniority
    assert result["work_arrangement"] == arrangement


def test_title_word_wins_when_explicit_evidence_conflicts():
    result = job(title="[Remoto] Developer", labels=["Remoto", "Presencial"])

    assert result["work_arrangement"] == WorkArrangement.REMOTE


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


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Estágio Júnior Pleno Sênior Especialista", SeniorityLevel.SPECIALIST),
        ("Coordenador Especialista", SeniorityLevel.COORDINATOR),
        ("Especialista Coordenador", SeniorityLevel.SPECIALIST),
        ("Junior Developer", SeniorityLevel.JUNIOR),
    ],
)
def test_title_seniority_order_and_equal_rank_occurrence(title, expected):
    result = job(title=title, labels=["Senior"], body="Nível: pleno")
    assert result["seniority_level"] == expected


@pytest.mark.parametrize(
    ("body", "seniority", "arrangement"),
    [
        ("Nível: pleno\nNível: sênior", SeniorityLevel.SENIOR, None),
        ("Nível\n- [x] Coordenador\n- [x] Especialista", SeniorityLevel.COORDINATOR, None),
        ("Nível\n- [x] Especialista\n- [x] Coordenador", SeniorityLevel.SPECIALIST, None),
        ("Alocação\n- [x] Remoto\n- [x] Presencial", None, WorkArrangement.ON_SITE),
        ("Alocação\n- [ ] Presencial\n- [x] Remoto", None, WorkArrangement.REMOTE),
    ],
)
def test_checked_body_values_resolve_when_labels_are_unusable(body, seniority, arrangement):
    result = job(labels=["Pleno", "Sênior", "Remoto", "Presencial"], body=body)
    assert result["seniority_level"] == seniority
    assert result["work_arrangement"] == arrangement


def test_usable_label_still_wins_over_a_different_body_value():
    result = job(labels=["Pleno", "Remoto"], body="Nível: sênior\nLocal: Presencial")
    assert result["seniority_level"] == SeniorityLevel.MID
    assert result["work_arrangement"] == WorkArrangement.REMOTE


@pytest.mark.parametrize(
    ("field", "old_value"),
    [
        ("seniority_level", SeniorityLevel.SENIOR),
        ("work_arrangement", WorkArrangement.ON_SITE),
    ],
)
def test_changed_category_mapping_invalidates_hash_for_the_same_source_text(field, old_value):
    from src.ingestion.hashing import content_hash

    after = job(title="Junior Developer [Remoto]", labels=["Senior", "Presencial"])
    before = {**after, field: old_value}  # Same source under the superseded label-first rule.
    assert after["seniority_level"] == SeniorityLevel.JUNIOR
    assert after["work_arrangement"] == WorkArrangement.REMOTE
    assert content_hash(before) != content_hash(after)
