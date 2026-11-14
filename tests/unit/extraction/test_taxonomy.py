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
