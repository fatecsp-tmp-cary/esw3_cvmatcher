from datetime import UTC, datetime

from src.ingestion.hashing import content_hash


def _job() -> dict:
    return {
        "title": "Data engineer",
        "description": "Build data systems",
        "publication_date": datetime(2026, 10, 27, tzinfo=UTC),
        "keywords": ["Python", "PostgreSQL"],
        "status": "ACTIVE",
        "content_hash": None,
    }


def test_content_hash_is_deterministic_across_key_order():
    job = _job()

    assert content_hash(job) == content_hash(dict(reversed(list(job.items()))))


def test_content_hash_changes_when_normalized_content_changes():
    original = _job()
    changed = {**original, "description": "Build reliable data systems"}

    assert content_hash(original) != content_hash(changed)


def test_content_hash_ignores_lifecycle_and_persistence_metadata():
    original = _job()
    changed = {**original, "status": "EXPIRED", "content_hash": "stored-hash"}

    assert content_hash(original) == content_hash(changed)
