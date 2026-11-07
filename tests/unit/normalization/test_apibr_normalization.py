import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.normalization.jobs.apibr import normalize_apibr_job, normalize_keywords, normalize_text


def test_normalize_apibr_job():
    fixture_path = Path("tests/resources/jobs_fixture.json")
    with open(fixture_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    raw_job = raw_data[0] if isinstance(raw_data, list) else raw_data
    normalized = normalize_apibr_job(raw_job)

    # Ensure source-supplied fields match the canonical schema.
    expected_keys = {
        "platform",
        "source_job_id",
        "source_expires_at",
        "company",
        "title",
        "description",
        "location",
        "work_arrangement",
        "seniority_level",
        "skills",
        "keywords",
        "salary",
        "currency",
        "job_url",
        "publication_date",
        "status",
        "last_verified_at",
        "raw",
        "embedding",
        "content_hash",
    }
    assert set(normalized.keys()) == expected_keys

    assert normalized["platform"] == "apibr"
    assert normalized["source_job_id"] == str(raw_job["id"])
    assert normalized["title"] is not None
    assert normalized["job_url"] is not None
    assert normalized["status"] == "ACTIVE"
    assert normalized["company"] is None
    assert normalized["location"] is None
    assert isinstance(normalized["publication_date"], datetime)
    assert normalized["publication_date"].tzinfo == UTC
    assert isinstance(normalized["keywords"], list)
    assert isinstance(normalized["skills"], list)


def test_normalize_text_empty():
    assert normalize_text(None) is None
    assert normalize_text("") is None
    assert normalize_text("   ") is None
    assert normalize_text("  SÃO   Developer  ") == "SÃO Developer"
    assert normalize_text(" <p>SÃO&nbsp;</p><div>Developer</div> ") == "SÃO Developer"


def test_normalize_keywords():
    assert normalize_keywords(None) == []
    assert normalize_keywords(["Python", {"name": "Backend"}]) == ["Python", "Backend"]
    assert normalize_keywords("not-a-list") == []


@pytest.mark.parametrize("source_id", [None, "", "   ", {}, True])
def test_normalize_apibr_job_rejects_missing_or_invalid_source_ids(source_id):
    with pytest.raises(ValueError, match="required id"):
        normalize_apibr_job({"id": source_id, "title": "Developer"})


def test_normalize_apibr_job_rejects_invalid_publication_date():
    with pytest.raises(ValueError, match="invalid created_at"):
        normalize_apibr_job({"id": 123, "title": "Developer", "created_at": "yesterday"})


@pytest.mark.parametrize("payload", [None, [], "issue", 123])
def test_normalize_apibr_job_rejects_non_object_payload(payload):
    with pytest.raises(ValueError, match="payload must be an object"):
        normalize_apibr_job(payload)


@pytest.mark.parametrize(
    ("state", "expected_status"),
    [("open", "ACTIVE"), ("closed", "EXPIRED"), (None, "DISCOVERED")],
)
def test_normalize_apibr_job_maps_github_issue_state(state, expected_status):
    normalized = normalize_apibr_job({"id": 123, "title": "Developer", "state": state})

    assert normalized["status"] == expected_status


def test_description_preserves_html_and_markdown_section_boundaries():
    job = normalize_apibr_job(
        {
            "id": 123,
            "title": "Developer",
            "body": "<h3>Requisitos</h3><p>Python</p><h3>Diferenciais</h3>Go\n"
            "<table><tr><td>Java</td><td>Kotlin</td></tr></table>\n## Benefícios\nPlano de saúde",
        }
    )
    assert job["description"] == (
        "Requisitos\nPython\nDiferenciais\nGo\nJava\nKotlin\n## Benefícios\nPlano de saúde"
    )
    assert job["raw"] is None
    assert normalize_text("<h3>Diferenciais</h3>Go") == "Diferenciais Go"
    assert normalize_text("<td>Java</td><td>Kotlin</td>") == "Java Kotlin"


def test_state_free_payload_stays_discovered():
    job = normalize_apibr_job({"id": 123, "title": "Developer", "body": "Python"})
    assert job["status"] == "DISCOVERED"
    assert job["last_verified_at"] is None


@pytest.mark.parametrize("empty_html", ["<p> </p>", "<!--hidden-->", "<br>&nbsp;"])
def test_html_without_text_cannot_supply_a_required_title(empty_html):
    assert normalize_text(empty_html) is None
    assert normalize_text(empty_html, preserve_sections=True) is None
    with pytest.raises(ValueError, match="required title"):
        normalize_apibr_job({"id": 123, "title": empty_html})
