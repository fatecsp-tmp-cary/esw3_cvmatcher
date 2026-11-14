"""Deterministic policy regressions, independent of model outputs and gold labels."""

import pytest

from src.extraction.classification import annotate_spans, classify
from src.extraction.contracts import SpanEvidence


def evidence(text, *mentions):
    output = []
    cursor = 0
    for mention in mentions:
        start = text.index(mention, cursor)
        output.append(SpanEvidence(start, start + len(mention), "skill", 0.9).serialize(text))
        cursor = start + len(mention)
    return output


@pytest.mark.parametrize(
    "text,mentions,expected",
    [
        (
            "Python required, Java preferred and Docker optional.",
            ("Python", "Java", "Docker"),
            ["REQUIRED", "PREFERRED", "NICE_TO_HAVE"],
        ),
        (
            "Python obrigatório, Java desejável e Docker opcional.",
            ("Python", "Java", "Docker"),
            ["REQUIRED", "PREFERRED", "NICE_TO_HAVE"],
        ),
        ("Python is not required, but Java is mandatory.", ("Python", "Java"), [None, "REQUIRED"]),
        (
            "Python não é necessário, mas Java é obrigatório.",
            ("Python", "Java"),
            [None, "REQUIRED"],
        ),
        (
            "AutoCAD é obrigatório. Revit é um diferencial.",
            ("AutoCAD", "Revit"),
            ["REQUIRED", "PREFERRED"],
        ),
        ("Python, Java and SQL required.", ("Python", "Java", "SQL"), ["REQUIRED"] * 3),
        ("Node.js is required. C# is preferred.", ("Node.js", "C#"), ["REQUIRED", "PREFERRED"]),
    ],
)
def test_local_scope_and_shared_predicates(text, mentions, expected):
    rows = annotate_spans(text, evidence(text, *mentions))
    assert [r["requirement_class"] for r in rows] == expected


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("mandatory", "REQUIRED"),
        ("must be known", "REQUIRED"),
        ("essential", "REQUIRED"),
        ("minimum requirement", "REQUIRED"),
        ("obrigatória", "REQUIRED"),
        ("indispensável", "REQUIRED"),
        ("necessário", "REQUIRED"),
        ("preferencial", "PREFERRED"),
        ("um diferencial", "PREFERRED"),
        ("desirable", "PREFERRED"),
        ("nice-to-have", "NICE_TO_HAVE"),
        ("a bonus", "NICE_TO_HAVE"),
        ("a plus", "NICE_TO_HAVE"),
        ("optional", "NICE_TO_HAVE"),
        ("opcional", "NICE_TO_HAVE"),
        ("maybe useful", "NICE_TO_HAVE"),
        ("could be needed", "NICE_TO_HAVE"),
        ("might be required", "NICE_TO_HAVE"),
        ("would be a plus", "NICE_TO_HAVE"),
        ("talvez útil", "NICE_TO_HAVE"),
        ("pode vir a ser necessário", "NICE_TO_HAVE"),
        ("not required", None),
        ("not necessary", None),
        ("não é exigido", None),
        ("não é necessário", None),
        ("unclear", None),
    ],
)
def test_multilingual_cues_negation_and_hedges(phrase, expected):
    text = f"Python is {phrase}."
    assert classify(text, 0, 6) == expected
    rows = annotate_spans(text, evidence(text, "Python"))
    assert len(rows) == 1
    assert rows[0]["requirement_class"] == expected
    assert rows[0]["exclusion_safe"] is False


def test_negation_before_entity_and_affirmative_not_only():
    text = "Não exigimos experiência com SAP. Java is not only required but preferred."
    rows = annotate_spans(text, evidence(text, "SAP", "Java"))
    assert [r["requirement_class"] for r in rows] == [None, "REQUIRED"]
    assert rows[0]["negated"]


def test_multiple_strengths_same_mention_uses_strongest():
    text = "Python is preferred and required."
    rows = annotate_spans(text, evidence(text, "Python"))
    assert rows[0]["requirement_class"] == "REQUIRED"
    assert rows[0]["conflicting"]


@pytest.mark.parametrize("second", ["optional", "not required", "preferred"])
def test_consolidation_keeps_strongest_occurrence_and_original_conflict(second):
    text = f"Java is mandatory. Java is {second}."
    raw = evidence(text, "Java", "Java")
    rows = annotate_spans(text, raw)
    assert len(rows) == 1 and rows[0]["start"] == 0
    assert rows[0]["requirement_class"] == "REQUIRED"
    assert all(r["conflicting"] and not r["exclusion_safe"] for r in raw)
    assert len(raw) == 2 and not raw[1]["requirement_selected"]


def test_selected_anchor_is_strongest_not_first_and_aliases_share_concept():
    text = "JS preferred. JavaScript mandatory."
    raw = evidence(text, "JS", "JavaScript")
    rows = annotate_spans(text, raw)
    assert len(rows) == 1 and rows[0]["start"] == text.index("JavaScript")
    assert rows[0]["conflicting"]


def test_section_fallback_persists_across_bullets_and_local_wording_wins():
    text = "# Requirements\n- Python\n- SQL\n- Java preferred\n# Benefits\nDocker required\n"
    raw = evidence(text, "Python", "SQL", "Java", "Docker")
    rows = annotate_spans(text, raw)
    assert [r["requirement_class"] for r in rows] == ["REQUIRED", "REQUIRED", "PREFERRED"]
    assert not raw[-1]["requirement_selected"]


@pytest.mark.parametrize(
    "heading", ["Benefits", "About us", "Responsibilities", "How to apply", "Other"]
)
def test_sections_terminate_on_unrelated_headings(heading):
    text = f"Requisitos:\nPython\n# {heading}\nJava required"
    rows = annotate_spans(text, evidence(text, "Python", "Java"))
    assert len(rows) == 1


@pytest.mark.parametrize("prefix", ["", "Requirments\n", "Requirements ???\n", "# Requirments:\n"])
def test_missing_and_malformed_sections_scan_local_evidence(prefix):
    text = prefix + "Python required. Java mentioned."
    raw = evidence(text, "Python", "Java")
    rows = annotate_spans(text, raw)
    assert len(rows) == 1 and rows[0]["requirement_class"] == "REQUIRED"
    assert raw[1]["requirement_class"] is None


def test_background_repetition_ignored_but_repeated_requirement_retained():
    text = "Team context: documentation and collaboration. " * 3 + "SQL required. SQL required."
    raw = evidence(text, "documentation", "documentation", "documentation", "SQL", "SQL")
    rows = annotate_spans(text, raw)
    assert len(rows) == 1 and text[rows[0]["start"] : rows[0]["end"]] == "SQL"
    assert len(raw) == 5


@pytest.mark.parametrize(
    "detected,smallest",
    [
        ("Registro COREN", "COREN"),
        ("ICU experience", "ICU"),
        ("Certificação PMP", "PMP"),
        ("Experiência em UTI", "UTI"),
        ("Amazon Web Services", "Amazon Web Services"),
        ("CNH D", "CNH D"),
        ("three years of nursing experience", "three years of nursing"),
        ("Nursing registration", "Nursing registration"),
    ],
)
def test_exact_unicode_smallest_meaningful_spans(detected, smallest):
    text = "🦉 Ação: " + detected + " is required."
    raw = evidence(text, detected)
    original = (raw[0]["start"], raw[0]["end"])
    (row,) = annotate_spans(text, raw)
    assert text[row["start"] : row["end"]] == smallest
    assert row["start"] == text.index(smallest)
    assert (row["detected_start"], row["detected_end"]) == original


def test_typo_support_is_distinct_from_canonical_equivalence():
    text = "Pyhton required."
    (row,) = annotate_spans(text, evidence(text, "Pyhton"))
    assert row["approximate_match"] and row["matched_skill"] == "Python"
    assert "canonical_skill" not in row and not row["exclusion_safe"]


def test_no_explicit_requirements_produces_no_selected_requirements():
    text = "The team uses Python. Responsibilities will be discussed later."
    raw = evidence(text, "Python")
    assert annotate_spans(text, raw) == []
    assert raw[0]["requirement_class"] is None
    assert annotate_spans("", []) == []


def test_cue_only_detections_are_not_entities_and_exact_aliases_recover_model_misses():
    text = "CRC é requisito obrigatório. CRF é obrigatório. CNH D é obrigatória."
    raw = evidence(text, "requisito obrigatório", "é obrigatório", "é obrigatória")
    rows = annotate_spans(text, raw)
    assert [text[r["start"] : r["end"]] for r in rows] == ["CRC", "CRF", "CNH D"]
    assert all(r["requirement_class"] == "REQUIRED" for r in rows)
    assert all(r["detection_source"] == "exact_alias" for r in rows)
    assert all(not r["requirement_selected"] for r in raw[:3])


def test_alias_supplement_never_invents_strength_or_fuzzy_offsets():
    text = "Python and Pyhton."
    raw = []
    assert annotate_spans(text, raw) == []
    assert len(raw) == 1 and text[raw[0]["start"] : raw[0]["end"]] == "Python"
    assert raw[0]["requirement_class"] is None


def test_seniority_wrapper_is_trimmed_without_changing_source_unicode():
    text = "Senioridade sênior é obrigatória."
    (row,) = annotate_spans(text, evidence(text, "Senioridade sênior"))
    assert text[row["start"] : row["end"]] == "sênior"
