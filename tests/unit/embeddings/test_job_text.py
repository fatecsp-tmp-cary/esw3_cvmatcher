"""Stable source-hash passage construction and versioned input policy."""

import hashlib
import json

from src.embeddings.config import DIMENSIONS, EmbeddingConfig
from src.embeddings.service import job_text
from src.ingestion.hashing import content_hash
from src.persistence.job.job import Job


def test_equivalent_location_objects_have_identical_hashes_and_passages():
    first = {"city": "São Paulo", "country": "Brasil", "region": None}
    second = {"region": None, "country": "Brasil", "city": "São Paulo"}
    assert content_hash({"location": first}) == content_hash({"location": second})
    assert job_text(Job(title="Role", location=first)) == job_text(
        Job(title="Role", location=second)
    )


def test_normalized_requirements_are_deterministic_and_not_omitted():
    job = Job(title="Role", description="Build systems")
    assert job_text(job, ["SQL", "Python", "SQL"]) == "Role\nPython\nSQL\nBuild systems"
    assert job_text(job, ["Python", "SQL"]) == job_text(job, ["SQL", "Python"])
    assert job_text(job, ["Python"]) != job_text(job, ["Java"])


def test_passage_policy_invalidates_the_pre_review_embedding_identity():
    previous = {
        "algorithm": "e5-full-token-windows-weighted-mean-v1",
        "max_tokens": 512,
        "overlap_tokens": 64,
        "dimensions": DIMENSIONS,
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
        "normalization": "l2-each-window-and-aggregate",
    }
    previous_hash = hashlib.sha256(
        json.dumps(previous, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert EmbeddingConfig().policy_version != previous_hash
