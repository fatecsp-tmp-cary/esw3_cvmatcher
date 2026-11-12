import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.domain.job import SeniorityLevel, WorkArrangement
from src.normalization.jobs.apibr import (
    normalize_apibr_job,
    normalize_keywords,
    normalize_text,
    vacancy_labels,
)


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
    [("open", "ACTIVE"), ("closed", "EXPIRED"), (None, "ACTIVE"), ("unexpected", "ACTIVE")],
)
def test_normalize_apibr_job_maps_listing_presence_and_explicit_state(state, expected_status):
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


def test_state_free_listed_payload_is_active():
    job = normalize_apibr_job({"id": 123, "title": "Developer", "body": "Python"})
    assert job["status"] == "ACTIVE"
    # Ingestion records the verification time of a successful observation.
    assert job["last_verified_at"] is None


def test_live_shape_records_without_state_are_active():
    statuses = {normalize_apibr_job(record)["status"] for record in _live_shape_fixture().values()}

    assert statuses == {"ACTIVE"}


@pytest.mark.parametrize("empty_html", ["<p> </p>", "<!--hidden-->", "<br>&nbsp;"])
def test_html_without_text_cannot_supply_a_required_title(empty_html):
    assert normalize_text(empty_html) is None
    assert normalize_text(empty_html, preserve_sections=True) is None
    with pytest.raises(ValueError, match="required title"):
        normalize_apibr_job({"id": 123, "title": empty_html})


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"html_url": {"bad": "url"}},
        {"url": ["invalid"]},
        {"created_at": "0001-01-01T00:00:00+01:00"},
    ],
)
def test_malformed_fields_raise_record_validation_errors(invalid_fields):
    with pytest.raises(ValueError, match="APiBR issue has an invalid"):
        normalize_apibr_job({"id": 2, "title": "Developer", **invalid_fields})


@pytest.mark.parametrize(
    "body",
    [
        "Apply at <https://example.org/apply>",
        "Required: Java List<T> and C++ vector<int>",
        "Literal <DomainType>value</DomainType> and <T/>",
    ],
)
def test_preserves_markdown_autolinks_and_literal_type_arguments(body):
    assert normalize_apibr_job({"id": 1, "title": "Engineer", "body": body})["description"] == body


def _live_shape_fixture() -> dict[int, dict]:
    path = Path("tests/resources/apibr_v2_issues.json")
    with open(path, encoding="utf-8") as fixture:
        return {record["id"]: record for record in json.load(fixture)}


@pytest.mark.parametrize(
    ("record_id", "seniority", "arrangement", "skills"),
    [
        # Explicit typed labels; repository topics and unknown labels are not classified.
        (
            910001,
            SeniorityLevel.SENIOR,
            WorkArrangement.REMOTE,
            ["AWS", "Docker", "Java", "PostgreSQL"],
        ),
        # Decorated and prefixed labels agree on one value each.
        (910002, SeniorityLevel.SENIOR, WorkArrangement.REMOTE, ["Python"]),
        # Every issue-form option arrives as a label: conflicting evidence stays unknown.
        (910003, None, None, []),
        # Only repository topics: nothing describes the vacancy itself.
        (910004, None, None, []),
    ],
)
def test_live_shape_labels_map_to_canonical_fields(record_id, seniority, arrangement, skills):
    job = normalize_apibr_job(_live_shape_fixture()[record_id])

    assert job["seniority_level"] == seniority
    assert job["work_arrangement"] == arrangement
    assert job["skills"] == skills
    assert job["location"] is None
    assert job["company"] is None


def test_live_shape_keeps_every_label_name_as_keyword():
    job = normalize_apibr_job(_live_shape_fixture()[910001])

    assert job["keywords"][:3] == ["Backend", "Brasil", "Nacional"]
    assert {"Backend-jobs", "Spring", "Verificada", "CLT"} <= set(job["keywords"])


def test_repository_topics_are_not_vacancy_evidence():
    labels = [
        {"name": "Remoto", "type": "topic"},
        {"name": "Sênior", "type": "topic"},
        {"name": "Python", "type": "topic"},
    ]
    job = normalize_apibr_job({"id": 1, "title": "Developer", "labels": labels})

    assert vacancy_labels({"labels": labels}) == []
    assert job["work_arrangement"] is None
    assert job["seniority_level"] is None
    assert job["skills"] == []


def test_untyped_string_labels_and_title_keywords_are_vacancy_evidence():
    job = normalize_apibr_job(
        {
            "id": 1,
            "title": "Developer",
            "labels": ["Pleno", "node.js", "K8s"],
            "keywords": ["Híbrido"],
        }
    )

    assert job["seniority_level"] == SeniorityLevel.MID
    assert job["work_arrangement"] == WorkArrangement.HYBRID
    assert job["skills"] == ["Kubernetes", "Node.js"]


@pytest.mark.parametrize(
    "labels",
    [
        ["Remoto", "Presencial"],
        ["Remoto/presencial"],
        ["Home Office - Tempo Determinado"],
        ["Alocado"],
    ],
)
def test_conflicting_or_unrecognized_arrangement_stays_unknown(labels):
    job = normalize_apibr_job({"id": 1, "title": "[Remoto] Developer", "labels": labels})

    assert job["work_arrangement"] is None


def test_free_text_is_never_interpreted_as_a_category_or_skill():
    job = normalize_apibr_job(
        {
            "id": 1,
            "title": "[Remoto] Senior Python Developer",
            "body": "Vaga remota para pessoa sênior com Python e Docker.",
        }
    )

    assert job["seniority_level"] is None
    assert job["work_arrangement"] is None
    assert job["skills"] == []


def test_skills_are_deduplicated_and_independent_of_label_order():
    labels = ["python", "Docker", "Python3", "Lang-python", "AWS"]
    first = normalize_apibr_job({"id": 1, "title": "Developer", "labels": labels})
    second = normalize_apibr_job({"id": 1, "title": "Developer", "labels": labels[::-1]})

    assert first["skills"] == second["skills"] == ["AWS", "Docker", "Python"]


@pytest.mark.parametrize("labels", [None, "Remoto", {"name": "Remoto"}, [None, 1, {}, {"name": 5}]])
def test_malformed_label_metadata_yields_no_classification(labels):
    job = normalize_apibr_job({"id": 1, "title": "Developer", "labels": labels})

    assert job["seniority_level"] is None
    assert job["work_arrangement"] is None
    assert job["skills"] == []
