import json
from pathlib import Path

from src.normalization.jobs.apibr import normalize_apibr_job, normalize_keywords, normalize_text


def test_normalize_apibr_job():
    fixture_path = Path("tests/resources/jobs_fixture.json")
    with open(fixture_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    raw_job = raw_data[0] if isinstance(raw_data, list) else raw_data
    normalized = normalize_apibr_job(raw_job)

    # Garante que todos os campos da Task 19 estão presentes no dicionário normalizado
    expected_keys = {
        "platform",
        "source_job_id",
        "company",
        "title",
        "description",
        "location",
        "work_arrangement",
        "seniority_level",
        "skills",
        "keywords",
        "salary",
        "job_url",
        "publication_date",
    }
    assert set(normalized.keys()) == expected_keys

    assert normalized["platform"] == "apibr"
    assert normalized["source_job_id"] == str(raw_job["id"])
    assert normalized["title"] is not None
    assert normalized["job_url"] is not None
    assert isinstance(normalized["keywords"], list)
    assert isinstance(normalized["skills"], list)


def test_normalize_text_empty():
    assert normalize_text(None) is None
    assert normalize_text("") is None
    assert normalize_text("   ") is None
    assert normalize_text("  Desenvolvedor   Python  ") == "Desenvolvedor Python"


def test_normalize_keywords():
    assert normalize_keywords(None) == []
    assert normalize_keywords(["Python", {"name": "Backend"}]) == ["Python", "Backend"]
    assert normalize_keywords("not-a-list") == []
