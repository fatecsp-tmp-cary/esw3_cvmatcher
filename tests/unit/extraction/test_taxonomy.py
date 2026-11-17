import pytest

from src.extraction.taxonomy import canonical_skill, find_skills, normalize_skill


@pytest.mark.parametrize(
    "value,expected",
    [
        (" K8S ", "kubernetes"),
        ("Ｃ＃", "c#"),
        ("Node.js", "node.js"),
        ("C++", "c++"),
        ("unknown skill", "unknown skill"),
        ("Postgres", "postgresql"),
        ("Amazon  Web Services", "aws"),
    ],
)
def test_explicit_skill_aliases(value, expected):
    assert normalize_skill(value) == expected


def test_unknown_alias_remains_unknown_supporting_evidence():
    assert canonical_skill("unknown tool") is None
    assert canonical_skill("K8S") == "Kubernetes"


def test_bounded_matching_preserves_technology_punctuation_and_phrases():
    assert find_skills(
        ["Conhecimento C++, C#, Node.js; Amazon Web Services e k8s."],
        ["C++", "C#", "Node.js", "AWS", "Kubernetes", "JavaScript"],
    ) == {"c++", "c#", "node.js", "aws", "kubernetes"}
    assert find_skills(
        ["cpython, pythonista, C++17, C##, mynode.js; reactjs"],
        ["Python", "C++", "C#", "Node.js", "React"],
    ) == {"react"}
    assert find_skills([], ["Python"]) == set()


def test_source_and_candidate_aliases_agree_for_compatibility_characters():
    assert canonical_skill("ｋ８ｓ") == "Kubernetes"
    assert normalize_skill("ｋ８ｓ") == normalize_skill("Kubernetes")


@pytest.mark.parametrize(
    "typo,name",
    [
        ("Pyhton", "Python"),
        ("Pythn", "Python"),
        ("Pythonn", "Python"),
        ("Pythom", "Python"),
        ("Postgress", "PostgreSQL"),
        ("Kubernets", "Kubernetes"),
    ],
)
def test_one_edit_typos_are_score_only_support(typo, name):
    from src.extraction.taxonomy import match_skill

    result = match_skill(typo)
    assert result.name == name and result.approximate
    assert canonical_skill(typo) is None
    assert find_skills([typo], [name]) == {normalize_skill(name)}


@pytest.mark.parametrize(
    "left,right",
    [
        ("C", "C#"),
        ("C", "C++"),
        ("C", "R"),
        ("Java", "JavaScript"),
        ("Ruby", "Rails"),
        ("PHP", "WordPress"),
        ("C##", "C#"),
        ("Cython", "Python"),
        ("CPython", "Python"),
        ("Pythnoo", "Python"),
        ("Nest.js", "Next.js"),
        ("Nuxt.js", "Next.js"),
        ("NuxtJS", "Next.js"),
        ("MSSQL", "MySQL"),
    ],
)
def test_distinct_names_and_large_edits_never_become_aliases(left, right):
    assert find_skills([left], [right]) == set()


def test_ties_across_concepts_remain_unknown_and_short_names_are_exact_only():
    from src.extraction.taxonomy import match_skill

    assert match_skill("abcde", vocabulary=["abcdf", "abcdg"]) is None
    assert match_skill("Goo") is None
    assert match_skill("C sharp").name == "C#"
    assert match_skill("C sharp").approximate is False
    assert match_skill("Py.thon") is None


def test_alias_spans_ignore_hyphenated_package_names_and_urls_and_emit_domain_labels():
    from src.extraction.taxonomy import alias_spans

    text = (
        "Use react-table, material-react-table, React, PostgreSQL, AWS, Node.js/Vue.js, "
        "github.com/empresa, https://careers.example-company.com/engineering/backend/python, "
        "and https://example.com/react-job"
    )
    spans = [(text[s:e], label) for s, e, label in alias_spans(text)]
    assert spans == [
        ("React", "framework"),
        ("PostgreSQL", "database"),
        ("AWS", "cloud"),
        ("Node.js", "framework"),
        ("Vue.js", "framework"),
    ]


@pytest.mark.parametrize(
    "value,expected",
    [
        ("observabilidade", "Observability"),
        ("microsserviços", "Microservices"),
        ("microsservicos", "Microservices"),
        ("metodologias ageis", "Agile"),
        ("governanca de dados", "Data Governance"),
        ("testes automatizados", "Automated Testing"),
        ("inglês avançado", "English"),
        ("inglês avançado.", "English"),
        ("fluência em inglês", "English"),
        ("Excel avançado", "Excel"),
        ("SQL básico", "SQL"),
        ("Python (desejável)", "Python"),
        ("Azure DevOps", "Azure DevOps"),
        ("SpringBoot", "Spring Boot"),
        ("ArgoCD", "Argo CD"),
    ],
)
def test_bilingual_accent_and_proficiency_normalization(value, expected):
    assert canonical_skill(value) == expected


def test_label_only_aliases_never_trigger_prose_false_positives():
    from src.extraction.taxonomy import alias_spans

    assert canonical_skill("IA") == "Artificial Intelligence"
    assert canonical_skill("Tempo") == "Grafana Tempo"
    assert canonical_skill("REST") == "REST"
    assert canonical_skill("APIs REST") == "REST"
    assert canonical_skill("Shell") == "Shell Script"
    assert canonical_skill("redes") == "Networking"
    assert canonical_skill("SOLID") == "SOLID"
    assert canonical_skill("SAFe") == "SAFe"

    prose = (
        "Preciso de tempo para ir ao trabalho; eu ia fazer o rest of the code and we shall see. "
        "Requirements: solid experience with Python and Docker, safe deployment. "
        "Requisitos: experiência com gestão de redes sociais."
    )
    assert [(prose[s:e], label) for s, e, label in alias_spans(prose)] == [
        ("Python", "skill"),
        ("Docker", "tool"),
    ]
    assert (
        find_skills(
            [prose],
            [
                "Artificial Intelligence",
                "Grafana Tempo",
                "REST",
                "Shell Script",
                "SOLID",
                "SAFe",
                "Networking",
            ],
        )
        == set()
    )
    assert find_skills(
        ["Experiência com APIs REST, princípios SOLID e Scaled Agile."],
        ["REST", "SOLID", "SAFe"],
    ) == {"rest", "solid", "safe"}


@pytest.mark.parametrize(
    "label,expected",
    [
        ("CI/CD", ("CI/CD",)),
        ("PL/SQL", ("PL/SQL",)),
        ("TCP/IP", ("TCP/IP",)),
        ("JavaScript/TypeScript", ("JavaScript", "TypeScript")),
        ("Scrum/Kanban", ("Scrum", "Kanban")),
        ("C/C++", ("C", "C++")),
        ("C#/.NET", ("C#", ".NET")),
        (
            "Cloud (AWS/Azure/GCP)",
            ("Cloud Computing", "AWS", "Azure", "Google Cloud Platform"),
        ),
        ("metodologias ágeis (Scrum, Kanban)", ("Agile", "Scrum", "Kanban")),
        ("bancos de dados relacionais e não relacionais", ("Relational Databases", "NoSQL")),
        ("Observabilidade (Datadog", ("Observability", "Datadog")),
        ("Visual Basic avançado", ("Visual Basic",)),
        ("Suporte técnico avançado", ("Technical Support",)),
        ("CNH A e B", ("CNH A", "CNH B")),
        ("unknown-tool-xyz", ()),
    ],
)
def test_resolve_skills_handles_compounds_and_preserves_atomic_slashes(label, expected):
    from src.extraction.taxonomy import resolve_skills

    assert resolve_skills(label) == expected


def test_taxonomy_hierarchy_categories_and_invariants():
    from src.extraction.taxonomy import (
        CATEGORIES,
        PARENTS,
        SPAN_LABELS,
        parent_skill,
        skill_category,
    )

    assert skill_category("PostgreSQL") == "database"
    assert skill_category("AWS") == "cloud"
    assert skill_category("Next.js") == "framework"
    assert parent_skill("Next.js") == "React"
    assert parent_skill("Spring Boot") == "Spring Framework"
    assert parent_skill("AWS Lambda") == "AWS"

    valid_span_labels = {
        "skill",
        "tool",
        "framework",
        "database",
        "cloud",
        "language",
        "certification",
        "professional license",
    }
    for name, category in CATEGORIES.items():
        assert 1 <= len(name) <= 150
        assert 1 <= len(category) <= 100
        assert SPAN_LABELS[name] in valid_span_labels

    for child, parent in PARENTS.items():
        assert child in CATEGORIES and parent in CATEGORIES
        seen: set[str] = set()
        cur: str | None = child
        while cur is not None:
            assert cur not in seen, f"Cycle detected at {cur}"
            seen.add(cur)
            cur = PARENTS.get(cur)
