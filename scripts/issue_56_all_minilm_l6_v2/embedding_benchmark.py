"""Shared embedding benchmark for CV-Match (issue #25, subtasks #56 and #57).

Runs ONE model against ONE input file and writes a JSON result, so every candidate model is
measured with the same procedure. Run it once per model (and once per input language).

Setup:
    pip install sentence-transformers psutil numpy

Usage:
    python scripts/benchmarks/embedding_benchmark.py \
        --model sentence-transformers/all-MiniLM-L6-v2
    python scripts/benchmarks/embedding_benchmark.py \
        --model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 --runs 7
    python scripts/benchmarks/embedding_benchmark.py --model <model> --input other_input.json

Input JSON: {"resume": {"title", "skills": [...], "experience": [...]},
             "jobs": [{"id", "title", "description"}, ...]}

What it measures:
    1. Environment and runtime requirements (OS, CPU, RAM, library versions, device).
    2. Model load time and memory (process RSS before/after loading, and peak).
    3. Generation time: warm-up call excluded, median of --runs repetitions
       (one resume, and all jobs in one batch).
    4. PT/EN support: cosine similarity of equivalent and unrelated PT<->EN sentence pairs.
    5. Token limit: texts longer than the model's max_seq_length are split into overlapping
       chunks; a resume/job score is the maximum cosine over chunk pairs.
    6. Ranking of the jobs for the resume, with precision@k against --relevant-ids
       (a heuristic: the default ids 1-12 are the software/engineering jobs of the shared input).

Notes:
    - The first run downloads the model, which inflates the load time. The result records
      whether the model was already in the local Hugging Face cache; report a cached run.
    - Memory and timing depend on the machine. Compare models only on the same machine.
"""

import argparse
import json
import platform
import statistics
import time
from importlib import metadata
from pathlib import Path

import numpy as np
import psutil
from sentence_transformers import SentenceTransformer

DEFAULT_INPUT = Path(__file__).parent / "embedding_benchmark_input.json"
DEFAULT_RELEVANT_IDS = list(range(1, 13))
BATCH_SIZE = 32
CHUNK_OVERLAP = 20  # tokens shared between consecutive chunks
SPECIAL_TOKENS = 2  # [CLS]/[SEP] (or <s>/</s>) added by the tokenizer around every text

# intfloat/e5 models were trained with these prefixes; leaving them out degrades quality.
E5_PREFIXES = ("query: ", "passage: ")

PAIRS_EQUIVALENT = [
    ("O gato está dormindo no sofá.", "The cat is sleeping on the couch."),
    ("Qual é o horário de funcionamento da loja?", "What are the store's opening hours?"),
    ("Preciso cancelar meu pedido.", "I need to cancel my order."),
    (
        "Desenvolvedora backend com experiência em Python e APIs REST.",
        "Backend developer with experience in Python and REST APIs.",
    ),
    (
        "Analista de suporte técnico com conhecimento em redes.",
        "Technical support analyst with networking knowledge.",
    ),
]
PAIRS_DIFFERENT = [
    ("O gato está dormindo no sofá.", "I need to cancel my order."),
    ("Qual é o horário de funcionamento da loja?", "The weather is nice today."),
    (
        "Desenvolvedora backend com experiência em Python e APIs REST.",
        "Chef preparing menus and managing a kitchen team.",
    ),
]


def rss_mb():
    """Resident memory of this process, in MB."""
    return psutil.Process().memory_info().rss / (1024 * 1024)


def package_version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not installed"


def cpu_name():
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(errors="ignore").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "unknown"


def model_in_cache(model_name):
    """True/False if the model's config is in the local Hugging Face cache; None if unknown."""
    try:
        from huggingface_hub import try_to_load_from_cache

        return isinstance(try_to_load_from_cache(repo_id=model_name, filename="config.json"), str)
    except Exception:
        return None


def environment():
    return {
        "os": platform.platform(),
        "machine": platform.machine(),
        "cpu": cpu_name(),
        "cpu_cores_logical": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "python": platform.python_version(),
        "torch": package_version("torch"),
        "sentence_transformers": package_version("sentence-transformers"),
        "numpy": np.__version__,
        "device": "cpu",
        "batch_size": BATCH_SIZE,
    }


def prefixes_for(model_name):
    """(query_prefix, passage_prefix) for the model, empty strings when not needed."""
    return E5_PREFIXES if model_name.startswith("intfloat/") else ("", "")


def build_resume_text(resume):
    parts = [resume.get("title", ""), *resume.get("skills", []), *resume.get("experience", [])]
    return ". ".join(p for p in parts if p)


def build_job_text(job):
    return f"{job['title']}. {job['description']}"


def normalize(matrix):
    return matrix / np.linalg.norm(matrix, axis=1, keepdims=True)


def cosine(a, b):
    return (normalize(np.atleast_2d(a)) @ normalize(np.atleast_2d(b)).T).item()


def split_into_chunks(text, tokenizer, size, overlap=CHUNK_OVERLAP):
    """Split `text` into chunks of at most `size` tokens, overlapping by `overlap` tokens."""
    tokens = tokenizer.tokenize(text)
    step = max(size - overlap, 1)
    chunks = []
    start = 0
    while start < len(tokens):
        chunks.append(tokenizer.convert_tokens_to_string(tokens[start : start + size]))
        if start + size >= len(tokens):
            break
        start += step
    return chunks


def embed_with_chunking(model, text, prefix=""):
    """Embeddings of `text` as an (n_chunks, dim) array.

    A text that fits in max_seq_length is a single chunk. A longer one is split, and the prefix
    is re-applied to every chunk so e5 models still see it.
    """
    tokenizer = model.tokenizer
    prefix_tokens = len(tokenizer.tokenize(prefix)) if prefix else 0
    budget = model.max_seq_length - SPECIAL_TOKENS - prefix_tokens
    if len(tokenizer.tokenize(text)) <= budget:
        return model.encode([prefix + text], batch_size=BATCH_SIZE, convert_to_numpy=True)
    chunks = split_into_chunks(text, tokenizer, budget)
    return model.encode([prefix + c for c in chunks], batch_size=BATCH_SIZE, convert_to_numpy=True)


def best_chunk_score(chunks_a, chunks_b):
    return float((normalize(chunks_a) @ normalize(chunks_b).T).max())


def time_runs(fn, runs):
    """Run `fn` `runs` times and return median/min/max in milliseconds."""
    samples = []
    for _ in range(runs):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000)
    return {
        "median_ms": round(statistics.median(samples), 2),
        "min_ms": round(min(samples), 2),
        "max_ms": round(max(samples), 2),
    }


def pair_similarities(model, pairs, prefix):
    sims = []
    for first, second in pairs:
        embeddings = model.encode([prefix + first, prefix + second], convert_to_numpy=True)
        sims.append(round(cosine(embeddings[0], embeddings[1]), 4))
    return sims


def precision_at(ranking, relevant_ids, k):
    return round(sum(1 for entry in ranking[:k] if entry["job_id"] in relevant_ids) / k, 3)


def run_benchmark(args):
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    jobs = data["jobs"]
    query_prefix, passage_prefix = prefixes_for(args.model)
    resume_text = build_resume_text(data["resume"])
    job_texts = [build_job_text(j) for j in jobs]

    print(f"Model: {args.model}\nInput: {args.input} ({len(jobs)} jobs)")

    # 1. Load: time and memory.
    cached = model_in_cache(args.model)
    memory_before = rss_mb()
    start = time.perf_counter()
    model = SentenceTransformer(args.model, device="cpu")
    load_seconds = time.perf_counter() - start
    memory_after_load = rss_mb()
    print(f"Load: {load_seconds:.2f}s (model already cached: {cached})")

    model.encode(["warm-up"], convert_to_numpy=True)  # first call is slower; excluded
    peak = max(memory_after_load, rss_mb())

    # 2. Generation time (plain encode: texts over the limit are truncated by the model).
    plain_resume_text = query_prefix + resume_text
    plain_job_texts = [passage_prefix + t for t in job_texts]
    resume_timing = time_runs(lambda: model.encode([plain_resume_text]), args.runs)
    jobs_timing = time_runs(lambda: model.encode(plain_job_texts, batch_size=BATCH_SIZE), args.runs)
    jobs_timing["per_job_median_ms"] = round(jobs_timing["median_ms"] / len(jobs), 2)
    print(
        f"Resume: {resume_timing['median_ms']} ms (median of {args.runs}) | "
        f"{len(jobs)} jobs in batch: {jobs_timing['median_ms']} ms"
    )

    plain_resume = model.encode([plain_resume_text], convert_to_numpy=True)
    plain_jobs = model.encode(plain_job_texts, batch_size=BATCH_SIZE, convert_to_numpy=True)
    peak = max(peak, rss_mb())

    # 3. PT/EN support.
    equivalent = pair_similarities(model, PAIRS_EQUIVALENT, query_prefix)
    different = pair_similarities(model, PAIRS_DIFFERENT, query_prefix)
    pt_en = {
        "equivalent_pairs": equivalent,
        "different_pairs": different,
        "equivalent_mean": round(statistics.mean(equivalent), 4),
        "different_mean": round(statistics.mean(different), 4),
        "gap": round(statistics.mean(equivalent) - statistics.mean(different), 4),
    }
    print(
        f"PT<->EN: equivalent {pt_en['equivalent_mean']} | unrelated "
        f"{pt_en['different_mean']} | gap {pt_en['gap']}"
    )

    # 4. Token limit and chunking.
    tokenizer = model.tokenizer
    resume_chunks = embed_with_chunking(model, resume_text, query_prefix)
    job_chunks = [embed_with_chunking(model, t, passage_prefix) for t in job_texts]
    job_token_counts = [len(tokenizer.tokenize(t)) for t in job_texts]
    limit = model.max_seq_length
    tokens = {
        "max_seq_length": int(limit),
        "resume_tokens": len(tokenizer.tokenize(resume_text)),
        "resume_chunks": len(resume_chunks),
        "jobs_chunked": sum(1 for c in job_chunks if len(c) > 1),
        "jobs_total": len(jobs),
        "max_job_tokens": max(job_token_counts),
    }
    print(
        f"Tokens: limit {limit}, resume {tokens['resume_tokens']} "
        f"({tokens['resume_chunks']} chunk(s)), longest job {tokens['max_job_tokens']}, "
        f"jobs needing chunking {tokens['jobs_chunked']}/{tokens['jobs_total']}"
    )
    peak = max(peak, rss_mb())

    # 5. Ranking (max cosine over chunk pairs) and the truncated baseline.
    ranking = sorted(
        (
            {
                "job_id": job["id"],
                "title": job["title"],
                "score": round(best_chunk_score(resume_chunks, chunks), 4),
            }
            for job, chunks in zip(jobs, job_chunks, strict=True)
        ),
        key=lambda entry: (-entry["score"], entry["job_id"]),
    )
    truncated_scores = [round(cosine(plain_resume[0], emb), 4) for emb in plain_jobs]
    truncated_top10 = [
        {"job_id": jobs[i]["id"], "score": truncated_scores[i]}
        for i in sorted(range(len(jobs)), key=lambda i: -truncated_scores[i])[:10]
    ]
    relevant = set(args.relevant_ids)
    quality = {
        "relevant_ids": sorted(relevant),
        "precision_at_5": precision_at(ranking, relevant, 5),
        "precision_at_10": precision_at(ranking, relevant, 10),
        "top10": ranking[:10],
        "full_ranking": ranking,
        "truncated_top10": truncated_top10,
    }
    print(f"Precision@5 {quality['precision_at_5']} | precision@10 {quality['precision_at_10']}")
    for position, entry in enumerate(ranking[:10], 1):
        print(f"  {position:>2}. {entry['score']:.4f}  [{entry['job_id']}] {entry['title']}")

    return {
        "model": args.model,
        "input_file": str(args.input),
        "environment": environment(),
        "model_info": {
            "max_seq_length": int(limit),
            "dimension": int(plain_jobs.shape[1]),
            "cached_before_load": cached,
        },
        "load_seconds": round(load_seconds, 3),
        "memory_mb": {
            "before_load": round(memory_before, 1),
            "after_load": round(memory_after_load, 1),
            "model_delta": round(memory_after_load - memory_before, 1),
            "peak": round(peak, 1),
        },
        "timing": {
            "runs": args.runs,
            "resume": resume_timing,
            "jobs_batch": jobs_timing,
            "jobs_count": len(jobs),
        },
        "pt_en": pt_en,
        "tokens": tokens,
        "ranking": quality,
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark one embedding model on one input.")
    parser.add_argument("--model", required=True, help="Hugging Face model name")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="input JSON file")
    parser.add_argument("--runs", type=int, default=5, help="timing repetitions (median)")
    parser.add_argument(
        "--relevant-ids",
        nargs="+",
        type=int,
        default=DEFAULT_RELEVANT_IDS,
        help="job ids considered relevant to the resume (for precision@k)",
    )
    parser.add_argument("--output", type=Path, help="result JSON path (default: auto-named)")
    return parser.parse_args()


def main():
    args = parse_args()
    result = run_benchmark(args)
    slug = args.model.replace("/", "_")
    output = args.output or Path.cwd() / f"benchmark_result_{slug}_{Path(args.input).stem}.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResult written to: {output}")


if __name__ == "__main__":
    main()
