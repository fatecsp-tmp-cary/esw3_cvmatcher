from datetime import UTC, datetime

import pytest

from src.domain.job import SeniorityLevel, WorkArrangement
from src.domain.requirements import explicit_seniority
from src.normalization.jobs.apibr import normalize_apibr_job
from src.normalization.jobs.meupadrinho import (
    MEUPADRINHO_VAGA_URL_TEMPLATE,
    normalize_meupadrinho_job,
    normalize_meupadrinho_location,
    normalize_meupadrinho_salary,
    normalize_meupadrinho_skills,
)


def _sample_record(**overrides):
    contents = {
        "titulo_vaga": "Python Developer",
        "local": "São Paulo, SP",
        "horario_registro": "2026-10-20T09:46:00.966098",
        "link_vaga": "https://example.org/jobs/python-developer-0faqqUu3",
        "link_plataforma_publicado": "https://example.org/jobs/python-developer-0faqqUu3",
        "plataforma": "LINKEDIN",
        "forma_trabalho": "remoto",
        "cargo": "BACKEND",
        "nivel": "Senior",
        "descricao_vaga": "Desenvolvedor Python Sênior para construir microserviços.",
        "requisitos_tecnicos": "Python; FastAPI; PostgreSQL; Docker; design patterns",
        "requisitos_desejaveis": "Experiência com GitHub Actions; inglês avançado",
        "nivel_vaga": "Sênior",
        "tipo_contrato": "PJ",
        "salario": "12.000,00 - 15.000,00",
        "nome_empresa": "Acme Synthetic Tech",
        "vaga_encerrada": False,
    }
    contents.update(overrides)
    return {"nano_id": "0faqqUu3", "contents": contents}


def test_normalize_meupadrinho_job_maps_canonical_schema():
    normalized = normalize_meupadrinho_job(_sample_record())
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
    assert normalized["platform"] == "meupadrinho"
    assert normalized["source_job_id"] == "0faqqUu3"
    assert normalized["company"] == "Acme Synthetic Tech"
    assert normalized["title"] == "Python Developer"
    assert normalized["description"] == (
        "Desenvolvedor Python Sênior para construir microserviços.\n"
        "Requisitos desejáveis:\n"
        "Experiência com GitHub Actions; inglês avançado"
    )
    assert normalized["location"] == {
        "city": "São Paulo",
        "state": "SP",
        "country": "Brasil",
        "raw": "São Paulo, SP",
    }
    assert normalized["work_arrangement"] is WorkArrangement.REMOTE
    assert normalized["seniority_level"] is SeniorityLevel.SENIOR
    assert normalized["skills"] == [
        "design patterns",
        "Docker",
        "FastAPI",
        "PostgreSQL",
        "Python",
    ]
    assert normalized["salary"] == {"min": 12000, "max": 15000}
    assert normalized["currency"] == "BRL"
    assert normalized["job_url"] == "https://example.org/jobs/python-developer-0faqqUu3"
    assert normalized["publication_date"] == datetime(2026, 10, 20, 9, 46, 0, 966098, tzinfo=UTC)
    assert normalized["status"] == "ACTIVE"
    assert normalized["raw"] is None


def test_normalize_meupadrinho_job_accepts_flat_detail_payload():
    record = _sample_record()
    flat = {"nano_id": record["nano_id"], **record["contents"]}
    assert normalize_meupadrinho_job(flat) == normalize_meupadrinho_job(record)


def test_job_url_priority_and_fallback():
    first = normalize_meupadrinho_job(
        _sample_record(
            link_vaga="https://example.com/1",
            link_vaga_publicado="https://example.com/2",
            link_plataforma_publicado="https://example.com/3",
        )
    )
    assert first["job_url"] == "https://example.com/1"

    second = normalize_meupadrinho_job(
        _sample_record(
            link_vaga="",
            link_vaga_publicado="https://example.com/2",
            link_plataforma_publicado="https://example.com/3",
        )
    )
    assert second["job_url"] == "https://example.com/2"

    third = normalize_meupadrinho_job(
        _sample_record(
            link_vaga=None,
            link_vaga_publicado=None,
            link_plataforma_publicado="https://example.com/3",
        )
    )
    assert third["job_url"] == "https://example.com/3"

    fallback = normalize_meupadrinho_job(
        _sample_record(
            link_vaga="",
            link_vaga_publicado="",
            link_plataforma_publicado="",
        )
    )
    assert fallback["job_url"] == MEUPADRINHO_VAGA_URL_TEMPLATE.format(nano_id="0faqqUu3")


@pytest.mark.parametrize(
    ("nivel_vaga", "nivel", "expected"),
    [
        ("Estágio", "Pleno", SeniorityLevel.INTERN),
        ("Júnior", "Senior", SeniorityLevel.JUNIOR),
        ("Pleno", "Junior", SeniorityLevel.MID),
        ("Sênior", "Pleno", SeniorityLevel.SENIOR),
        ("Staff", "Senior", SeniorityLevel.SPECIALIST),
        ("Techlead", "Senior", SeniorityLevel.COORDINATOR),
        ("Diretor", "Senior", SeniorityLevel.COORDINATOR),
        ("", "Techlead", SeniorityLevel.COORDINATOR),
        ("CLT", "Staff", SeniorityLevel.SPECIALIST),
        ("", "", None),
    ],
)
def test_seniority_uses_nivel_vaga_with_fallback_to_nivel(nivel_vaga, nivel, expected):
    job = normalize_meupadrinho_job(_sample_record(nivel_vaga=nivel_vaga, nivel=nivel))
    assert job["seniority_level"] == expected


def test_meupadrinho_seniority_and_typo_aliases_do_not_alter_apibr_or_candidate_scoring():
    apibr_tech_lead = normalize_apibr_job(
        {"id": 1, "title": "Tech Lead Sênior Python", "body": "", "labels": []}
    )
    apibr_staff = normalize_apibr_job(
        {"id": 2, "title": "Senior Staff Engineer", "body": "", "labels": []}
    )
    assert apibr_tech_lead["seniority_level"] is SeniorityLevel.SENIOR
    assert apibr_staff["seniority_level"] is SeniorityLevel.SENIOR
    assert explicit_seniority("Senior Staff Engineer") is SeniorityLevel.SENIOR


@pytest.mark.parametrize(
    ("forma", "expected"),
    [
        ("remoto", WorkArrangement.REMOTE),
        ("híbrido", WorkArrangement.HYBRID),
        ("hibrido", WorkArrangement.HYBRID),
        ("presencial", WorkArrangement.ON_SITE),
        ("presecial", WorkArrangement.ON_SITE),
        (None, None),
        ("", None),
    ],
)
def test_work_arrangement_normalizes_variants_and_typos(forma, expected):
    job = normalize_meupadrinho_job(_sample_record(forma_trabalho=forma))
    assert job["work_arrangement"] == expected


@pytest.mark.parametrize(
    ("raw_salary", "expected_salary", "expected_currency"),
    [
        ("", None, None),
        (None, None, None),
        ("0,00", None, None),
        ("A combinar", None, None),
        ("8.000,00", {"min": 8000, "max": 8000}, "BRL"),
        ("9.471,38", {"min": 9471.38, "max": 9471.38}, "BRL"),
        ("1500.50", {"min": 1500.5, "max": 1500.5}, "BRL"),
        ("12k - 15k", {"min": 12000, "max": 15000}, "BRL"),
        ("R$ 4.000,00 + VR R$ 600,00", None, None),
        ("100,00-150,00", {"min": 100, "max": 150}, "BRL"),
        ("120.000,00 – 160.000,00", {"min": 120000, "max": 160000}, "BRL"),
        ("12.000,00 a 15.000,00", {"min": 12000, "max": 15000}, "BRL"),
        ("2.500,00 ~ 4.000,00", {"min": 2500, "max": 4000}, "BRL"),
        ("R$35.333,33–R$44.166,67", {"min": 35333.33, "max": 44166.67}, "BRL"),
    ],
)
def test_salary_and_currency_normalization(raw_salary, expected_salary, expected_currency):
    salary, currency = normalize_meupadrinho_salary(raw_salary)
    assert salary == expected_salary
    assert currency == expected_currency


@pytest.mark.parametrize(
    ("raw_local", "expected"),
    [
        (None, None),
        ("", None),
        ("Brasil", {"city": None, "state": None, "country": "Brasil", "raw": "Brasil"}),
        (
            "Curitiba, PR",
            {"city": "Curitiba", "state": "PR", "country": "Brasil", "raw": "Curitiba, PR"},
        ),
        (
            "São Paulo, Brasil",
            {"city": "São Paulo", "state": None, "country": "Brasil", "raw": "São Paulo, Brasil"},
        ),
        (
            "Austin, Texas, Estados Unidos",
            {
                "city": "Austin",
                "state": "Texas",
                "country": "Estados Unidos",
                "raw": "Austin, Texas, Estados Unidos",
            },
        ),
        (
            "São Paulo e Região",
            {"city": None, "state": None, "country": None, "raw": "São Paulo e Região"},
        ),
    ],
)
def test_location_normalization(raw_local, expected):
    assert normalize_meupadrinho_location(raw_local) == expected


def test_skills_deduplicates_and_maps_canonical_aliases():
    skills = normalize_meupadrinho_skills("python; Python3; k8s; Custom Tool; custom tool")
    assert skills == ["Custom Tool", "Kubernetes", "Python"]


def test_vaga_encerrada_maps_to_expired():
    closed = normalize_meupadrinho_job(_sample_record(vaga_encerrada=True))
    assert closed["status"] == "EXPIRED"


@pytest.mark.parametrize(
    "bad_payload",
    [
        None,
        [],
        {"nano_id": "", "contents": {"titulo_vaga": "Dev"}},
        {"nano_id": "abc", "contents": "not-a-dict"},
        {"nano_id": "abc", "contents": {"titulo_vaga": ""}},
        {"nano_id": "abc", "contents": {"titulo_vaga": "Dev", "horario_registro": "bad-date"}},
        {"nano_id": "abc", "contents": {"titulo_vaga": "Dev", "vaga_encerrada": "no"}},
    ],
)
def test_invalid_meupadrinho_payloads_raise_value_error(bad_payload):
    with pytest.raises(ValueError):
        normalize_meupadrinho_job(bad_payload)
