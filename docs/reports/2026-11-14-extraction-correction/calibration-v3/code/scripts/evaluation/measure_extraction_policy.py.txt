"""Explicit offline calibration, then frozen old-set regression; never release approval."""

import argparse
import hashlib
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

from scripts.evaluation.evaluate import evaluate, validate_fixture

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, document):
    with path.open("x") as stream:
        stream.write(json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def semantic(raw, calibration):
    from src.matching.semantic import ExperienceScore, semantic_score

    values = [calibration.score(cosine) for cosine in raw["cosines"]]
    count = raw["experience_count"]
    return (
        semantic_score(
            tuple(ExperienceScore(value, date(2020, 1, 1), None) for value in values[:count]),
            tuple(values[count:]),
        )
        if values
        else 0.0
    )


def case_errors(cases, predictions):
    supplied = {p["id"]: p for p in predictions}
    errors = []
    for case in cases:
        prediction = supplied.get(case["id"])
        if prediction is None:
            errors.append({"id": case["id"], "category": "missing_prediction"})
            continue
        gold = {
            (r["start"], r["end"], r["requirement_class"]) for r in case["expected"]["requirements"]
        }
        actual = {
            (r["start"], r["end"], r["requirement_class"]) for r in prediction["requirements"]
        }
        role_error = (prediction["role_score"] >= 50) != (
            case["expected"]["role_relation"] == "relevant"
        )
        if gold != actual or role_error:

            def order(row):
                return row[0], row[1], row[2] or ""

            errors.append(
                {
                    "id": case["id"],
                    "language": case["language"],
                    "missing_requirements": sorted(gold - actual, key=order),
                    "unexpected_requirements": sorted(actual - gold, key=order),
                    "role_error": role_error,
                    "role_score": prediction["role_score"],
                }
            )
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("calibration", "regression"), required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--extraction-directory", type=Path, required=True)
    parser.add_argument("--embedding-cache", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--frozen", type=Path)
    args = parser.parse_args()
    if (args.phase == "regression") != bool(args.frozen):
        parser.error("Only regression requires --frozen; calibration cannot reuse held-out fitting")
    fixture = json.loads(args.fixtures.read_text())
    all_cases = validate_fixture(fixture)
    provenance = fixture["provenance"]
    if (
        not provenance.get("policy_adjudication")
        or provenance.get("heldout_independent") is not False
    ):
        parser.error("Requires policy-adjudicated calibration/regression labels")
    partition_name = "calibration" if args.phase == "calibration" else "heldout"
    ids = provenance["partition"][partition_name + "_ids"]
    cases = [c for c in all_cases if c["id"] in ids]
    args.output_directory.mkdir(parents=True, exist_ok=False)
    out = args.output_directory
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    import torch

    from src.embeddings.config import EmbeddingConfig
    from src.embeddings.encoder import LocalEmbeddingEncoder
    from src.extraction.classification import annotate_spans
    from src.extraction.gliner import _POLICY, EXTRACTION_VERSION, GlinerExtractor
    from src.matching.ranking import SimilarityCalibration

    torch.set_num_threads(1)
    paths = [
        *sorted((ROOT / "src/extraction").glob("*.py")),
        ROOT / "src/embeddings/config.py",
        ROOT / "src/embeddings/encoder.py",
        ROOT / "src/matching/ranking.py",
        ROOT / "src/matching/semantic.py",
        ROOT / "scripts/evaluation/evaluate.py",
        Path(__file__),
    ]
    code_hashes = {str(path.relative_to(ROOT)): digest(path) for path in paths}
    if args.frozen:
        frozen = json.loads(args.frozen.read_text())
        if (
            frozen["extraction_version"] != EXTRACTION_VERSION
            or frozen["gold_sha256"] != digest(args.fixtures)
            or frozen["code_hashes"] != code_hashes
        ):
            raise ValueError("Frozen extraction, gold or measurement code changed")
        calibration = SimilarityCalibration(
            version=frozen["version"], zero=frozen["zero"], full=frozen["full"]
        )
    else:
        calibration = SimilarityCalibration()
    protocol = {
        "phase": args.phase,
        "partition_ids": ids,
        "extraction_policy": _POLICY,
        "extraction_version": EXTRACTION_VERSION,
        "gold_sha256": digest(args.fixtures),
        "code_hashes": code_hashes,
        "cutoff": 50,
        "calibration_search": "zero=0.00..0.90 step 0.01, full=1.0; calibration only",
        "selection": (
            "mean PT/EN accuracy, then minimum language accuracy, then proximity to zero=0.5"
        ),
        "independent_acceptance": False,
        "hard_exclusions_enabled": False,
    }
    write(out / "protocol.json", protocol)
    extractor = GlinerExtractor(args.extraction_directory)
    encoder = LocalEmbeddingEncoder(EmbeddingConfig(cache_directory=args.embedding_cache))
    predictions, raw_scores, failures, detections = [], [], [], []
    for case in cases:
        try:
            job = case["job"]
            text = job["title"] + "\n" + job["description"]
            offset = len(job["title"]) + 1
            raw = [span.serialize(text) for span in extractor.extract(text)]
            selected = annotate_spans(text, raw)
            requirements = [
                {
                    "start": row["start"] - offset,
                    "end": row["end"] - offset,
                    "text": text[row["start"] : row["end"]],
                    "requirement_class": row["requirement_class"],
                }
                for row in selected
                if row["start"] >= offset
            ]
            detections.append(
                {
                    "id": case["id"],
                    "offset_origin": "title + newline + description",
                    "evidence": raw,
                }
            )
            ex = [
                entry["title"] + "\n" + entry["description"]
                for entry in case["candidate"]["experiences"]
            ]
            ed = [entry["title"] for entry in case["candidate"]["education"]]
            cosines = []
            if ex + ed:
                job_vector = encoder.encode_jobs([text])[0]
                cosines = [
                    sum(a * b for a, b in zip(vector, job_vector, strict=True))
                    for vector in encoder.encode_queries(ex + ed)
                ]
            scores = {"id": case["id"], "cosines": cosines, "experience_count": len(ex)}
            raw_scores.append(scores)
            predictions.append(
                {
                    "id": case["id"],
                    "requirements": requirements,
                    "role_score": semantic(scores, calibration),
                }
            )
            print(f"{args.phase}: {case['id']} completed", flush=True)
        except Exception:
            # Preserve case/category, never exception strings or candidate content.
            failures.append({"id": case["id"], "category": "inference_or_validation_error"})
    write(out / "inference-errors.json", failures)
    write(out / "detections.json", detections)
    write(out / "scalar-evidence.json", raw_scores)
    if not args.frozen:
        trials = []
        by_id = {c["id"]: c for c in cases}
        if failures or len(raw_scores) != len(cases):
            raise ValueError(
                "Incomplete calibration; retained case errors, configuration not frozen"
            )
        for index in range(91):
            zero = index / 100
            trial = SimilarityCalibration(zero=zero, full=1.0)
            accuracy = {}
            for language in ("pt", "en"):
                group = [r for r in raw_scores if by_id[r["id"]]["language"] == language]
                accuracy[language] = sum(
                    (semantic(r, trial) >= 50)
                    == (by_id[r["id"]]["expected"]["role_relation"] == "relevant")
                    for r in group
                ) / len(group)
            trials.append(
                {
                    "zero": zero,
                    "accuracy": accuracy,
                    "objective": [
                        (accuracy["pt"] + accuracy["en"]) / 2,
                        min(accuracy.values()),
                        -abs(zero - 0.5),
                    ],
                }
            )
        best = max(trials, key=lambda t: t["objective"])
        params = {"zero": best["zero"], "full": 1.0, "cutoff": 50}
        version = (
            "extraction-policy-v2-calibration-"
            + hashlib.sha256(
                json.dumps({**params, "extraction": EXTRACTION_VERSION}, sort_keys=True).encode()
            ).hexdigest()[:12]
        )
        calibration = SimilarityCalibration(version=version, zero=best["zero"], full=1.0)
        frozen = {
            **params,
            "version": version,
            "frozen_at": datetime.now(UTC).isoformat(),
            "extraction_version": EXTRACTION_VERSION,
            "extraction_policy": _POLICY,
            "gold_sha256": digest(args.fixtures),
            "code_hashes": code_hashes,
            "protocol_sha256": digest(out / "protocol.json"),
            "embedding_model": encoder.model_version,
            "artifact_manifest_sha256": digest(args.extraction_directory / "provenance.json"),
            "calibration_ids": ids,
            "heldout_used_for_fitting": False,
            "independent_acceptance": False,
            "release_quality_approved": False,
            "hard_exclusions_enabled": False,
        }
        write(out / "calibration-search.json", trials)
        write(out / "frozen-calibration.json", frozen)
        for prediction, scores in zip(predictions, raw_scores, strict=True):
            prediction["role_score"] = semantic(scores, calibration)
    prediction_doc = {"schema_version": "1.0", "predictions": predictions}
    report = evaluate(fixture, prediction_doc, case_ids=ids)
    report["measurement"] = {
        "phase": args.phase,
        "frozen": frozen,
        "semantic_component_only": True,
        "runtime_calibration_changed": False,
    }
    write(out / "predictions.json", prediction_doc)
    write(out / "report.json", report)
    write(out / "case-errors.json", case_errors(cases, predictions))
    print(
        json.dumps(
            {"phase": args.phase, "cases": len(predictions), "independent_acceptance": False}
        )
    )


if __name__ == "__main__":
    main()
