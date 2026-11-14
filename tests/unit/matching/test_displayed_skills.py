import pytest

from src.matching.pipeline import displayed_skills


@pytest.mark.parametrize(
    ("own", "extracted", "expected"),
    [
        (["Java"], {"python": "Python"}, ["Java", "Python"]),
        # The job's own spelling wins and a skill is never listed twice.
        (["python"], {"python": "Python"}, ["python"]),
        # Extracted-only skills fill a job without label skills.
        (None, {"aws": "AWS", "java": "Java"}, ["AWS", "Java"]),
        ([], {"sql": "SQL"}, ["SQL"]),
        # Deterministic, case-insensitive order independent of input order.
        (["Spring", "docker"], {"aws": "AWS"}, ["AWS", "docker", "Spring"]),
        # Nothing to show: the stored value is returned unchanged.
        (None, {}, None),
        ([], {}, []),
        (["  "], {}, ["  "]),
    ],
)
def test_displayed_skills_merge_job_and_extracted_skills(own, extracted, expected):
    assert displayed_skills(own, extracted) == expected


def test_displayed_skills_do_not_depend_on_extraction_order():
    first = displayed_skills(["Java"], {"python": "Python", "aws": "AWS"})
    second = displayed_skills(["Java"], {"aws": "AWS", "python": "Python"})

    assert first == second == ["AWS", "Java", "Python"]
