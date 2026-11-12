"""Explicit offline local-model evaluation on committed synthetic fixtures only."""

import argparse
import json
import os
from datetime import date
from pathlib import Path

from evaluate import DEFAULT_FIXTURE, evaluate, validate_fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extraction-directory", required=True)
    parser.add_argument("--embedding-cache")
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    import torch

    from src.embeddings.config import EmbeddingConfig
    from src.embeddings.encoder import LocalEmbeddingEncoder
    from src.extraction.gliner import EXTRACTION_VERSION, GlinerExtractor
    from src.matching.ranking import SimilarityCalibration
    from src.matching.semantic import ExperienceScore, semantic_score

    torch.set_num_threads(1)
    fixture = json.loads(DEFAULT_FIXTURE.read_text())
    cases = validate_fixture(fixture)
    extractor = GlinerExtractor(args.extraction_directory)
    encoder = LocalEmbeddingEncoder(EmbeddingConfig(cache_directory=args.embedding_cache))
    calibration = SimilarityCalibration()
    predictions = []
    for index, case in enumerate(cases, start=1):
        job = case["job"]
        full_text = job["title"] + "\n" + job["description"]
        offset = len(job["title"]) + 1
        requirements = []
        for span in extractor.extract(full_text):
            if span.start < offset:
                continue
            start, end = span.start - offset, span.end - offset
            requirements.append(
                {
                    "start": start,
                    "end": end,
                    "text": job["description"][start:end],
                    "requirement_class": None,
                }
            )
        # Multiple GLiNER labels on one span remain one unclassified mention.
        requirements = list({(s["start"], s["end"]): s for s in requirements}.values())
        experiences = [
            entry["title"] + "\n" + entry["description"]
            for entry in case["candidate"]["experiences"]
        ]
        education = [entry["title"] for entry in case["candidate"]["education"]]
        query_texts = experiences + education
        score = 0.0
        if query_texts:
            # Both representations are transient; only scalar synthetic scores are saved.
            job_vector = encoder.encode_jobs([full_text])[0]
            vectors = encoder.encode_queries(query_texts)
            scores = [
                calibration.score(sum(a * b for a, b in zip(vector, job_vector, strict=True)))
                for vector in vectors
            ]
            score = semantic_score(
                tuple(
                    ExperienceScore(value, date(2020, 1, 1), None)
                    for value in scores[: len(experiences)]
                ),
                tuple(scores[len(experiences) :]),
            )
        predictions.append({"id": case["id"], "requirements": requirements, "role_score": score})
        if index % 10 == 0:
            print(f"Evaluated {index}/{len(cases)} synthetic cases", flush=True)
    prediction_document = {"schema_version": "1.0", "predictions": predictions}
    report = evaluate(fixture, prediction_document)
    report["model_measurement"] = {
        "embedding_model": encoder.model_version,
        "extraction_version": EXTRACTION_VERSION,
        "calibration_version": calibration.version,
        "offline_cpu_threads": 1,
        "ranking_component": "per-pair semantic only; not complete retrieval/final blended ranking",
        "mandatory_classification_enabled": False,
        "limitations": (
            "Agent-reviewed synthetic corpus; no human release approval or calibration fit."
        ),
    }
    for path, document in ((args.predictions, prediction_document), (args.report, report)):
        with path.open("x") as stream:
            stream.write(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
