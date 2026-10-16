import json
from pathlib import Path
from src.normalization.jobs.apibr import normalize_apibr_job, normalize_text


def test_normalize_apibr_job():
    # 1. Carregar o payload da fixture
    fixture_path = Path("tests/resources/jobs_fixture.json")
    with open(fixture_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    # Se a fixture for uma lista, pegamos no primeiro item
    raw_job = raw_data[0] if isinstance(raw_data, list) else raw_data

    # 2. Executar a função de normalização
    normalized = normalize_apibr_job(raw_job)

    # 3. Validar a conversão para o modelo canónico
    assert normalized["platform"] == "apibr"
    assert normalized["source_job_id"] == str(raw_job["id"])
    assert normalized["title"] is not None
    assert normalized["job_url"] is not None


def test_normalize_text_empty():
    # Testa se a função lida corretamente com textos vazios ou nulos (cobre 100% do código)
    assert normalize_text(None) is None
    assert normalize_text("") is None
    assert normalize_text("   ") is None
    assert normalize_text("  Desenvolvedor   Python  ") == "Desenvolvedor Python"