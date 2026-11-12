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
