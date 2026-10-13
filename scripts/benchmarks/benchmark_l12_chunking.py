"""Resume chunking by structure + pgvector retrieval benchmark (issue #25, subtask #57).

Builds on embedding_benchmark.py (same directory): it reuses its environment, timing, PT/EN and
cosine helpers. The default model is paraphrase-multilingual-MiniLM-L12-v2 (128 tokens, 384 dims,
no prefixes); other 384-dim models work through --model (e5 prefixes are handled).

What it does:
    1. Embeds each job ("title. description") and stores it in an isolated pgvector table
       (vagas_pgvector_validation, HNSW index, dropped at the end).
    2. Splits the resume by structure into chunks: chunk 0 = title + skills, then one chunk per
       item of "experience" (a string, or a CandidateProfile Experience object).
    3. Scores every job against the resume with five strategies:
         baseline  the whole resume concatenated and truncated by the model (no chunking)
         A         maximum cosine over the resume chunks
         B         mean of the 3 highest chunk cosines
         C         requirement coverage: split the job description into requirements and average,
                   over requirements, the cosine of the most similar resume chunk
         D         one cosine against the mean of the chunk vectors (single pgvector query)
    4. Retrieves through pgvector (per-chunk top-N queries, merged in Python) and checks that the
       ranking matches the same strategies computed with numpy over all jobs.
    5. If a gabarito (ground truth made by a person) is given with --gabarito, also reports
       precision@10, recall@10 and nDCG@10 for each strategy. Without it, only the rankings and
       the pgvector-versus-numpy check are reported.

Setup (CPU-only PyTorch first, then the optional dependency group):
    pip install torch --index-url https://download.pytorch.org/whl/cpu
    pip install -e . --group benchmark
    docker compose up -d postgres        # DATABASE_URL is read from .env

Usage (run it from a directory outside the repo: the result JSON goes to the current directory):
    python <repo>/scripts/benchmarks/benchmark_l12_chunking.py --runs 5
    python <repo>/scripts/benchmarks/benchmark_l12_chunking.py --input other_input.json

The repository has no gabarito. --gabarito takes a JSON file written by a person:
    {"relevantes": [job ids that should be in the top 10], "irrelevantes_obvias": [job ids]}
"""

import argparse
import json
import math
import os
import re
import statistics
import time
from pathlib import Path

import numpy as np
import psycopg
from dotenv import load_dotenv
from embedding_benchmark import (
    BATCH_SIZE,
    PAIRS_DIFFERENT,
    PAIRS_EQUIVALENT,
    SPECIAL_TOKENS,
    build_job_text,
    environment,
    model_in_cache,
    normalize,
    package_version,
    pair_similarities,
    prefixes_for,
    rss_mb,
    time_runs,
)
from pgvector.psycopg import register_vector
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_INPUT = Path(__file__).parent / "embedding_benchmark_input.json"
TABLE = "vagas_pgvector_validation"
TOP_CHUNKS_B = 3
STRATEGIES = ("baseline", "A", "B", "C", "D")


# --- Chunking -------------------------------------------------------------------------------


def experience_text(item):
    """Text of one experience entry: a plain string, or a CandidateProfile Experience object."""
    if isinstance(item, str):
        return item
    parts = [item.get("title"), item.get("company"), item.get("description")]
    parts.append(", ".join(item.get("skills", [])))
    return ". ".join(p for p in parts if p)


def whole_resume_text(resume):
    """The resume as one text (title, skills, experience), the no-chunking baseline."""
    parts = [resume.get("title", ""), *resume.get("skills", [])]
    parts += [experience_text(item) for item in resume.get("experience", [])]
    return ". ".join(p for p in parts if p)


def build_resume_chunks(resume):
    """Chunk 0 = title + skills; then one chunk per experience item."""
    head = ". ".join(p for p in (resume.get("title"), ", ".join(resume.get("skills", []))) if p)
    return [head, *(experience_text(item) for item in resume.get("experience", []))]


def split_requirements(description):
    """Split a job description into requirement clauses (commas, semicolons, periods)."""
    parts = (p.strip() for p in re.split(r"[,;.]\s*", description))
    return [p for p in parts if len(p.split()) >= 2]


def token_counts(tokenizer, texts, prefix):
    """Tokens the model sees for each text, including the special tokens."""
    return [len(tokenizer.tokenize(prefix + t)) + SPECIAL_TOKENS for t in texts]


# --- Scoring (numpy reference) ----------------------------------------------------------------


def cosine_matrix(a, b):
    return normalize(np.atleast_2d(a)) @ normalize(np.atleast_2d(b)).T


def aggregate_a(sims):
    """sims: (n_chunks, n_jobs). Maximum over chunks."""
    return sims.max(axis=0)


def aggregate_b(sims):
    """Mean of the TOP_CHUNKS_B highest chunk cosines (all of them when there are fewer)."""
    return np.sort(sims, axis=0)[-TOP_CHUNKS_B:].mean(axis=0)


def coverage_c(chunk_vecs, requirement_vecs, fallback):
    """Mean over requirements of the best-matching chunk cosine; fallback if there are none."""
    if len(requirement_vecs) == 0:
        return fallback
    return float(cosine_matrix(chunk_vecs, requirement_vecs).max(axis=0).mean())


def numpy_scores(chunk_vecs, plain_resume_vec, job_vecs, requirement_vecs):
    """Score of every job under each strategy, computed with numpy over all jobs."""
    sims = cosine_matrix(chunk_vecs, job_vecs)
    score_a = aggregate_a(sims)
    mean_vec = normalize(chunk_vecs).mean(axis=0)
    return {
        "baseline": cosine_matrix(plain_resume_vec, job_vecs)[0],
        "A": score_a,
        "B": aggregate_b(sims),
        "C": np.array(
            [coverage_c(chunk_vecs, reqs, score_a[i]) for i, reqs in enumerate(requirement_vecs)]
        ),
        "D": cosine_matrix(mean_vec, job_vecs)[0],
    }


def rank(job_ids, scores):
    """Job ids by descending score; ties broken by id so the order is deterministic."""
    return [job_ids[i] for i in sorted(range(len(job_ids)), key=lambda i: (-scores[i], job_ids[i]))]


# --- Evaluation -------------------------------------------------------------------------------


def ndcg_at(order, relevant, k):
    """nDCG with binary relevance: a job is either in the gabarito or not."""
    dcg = sum(1 / math.log2(i + 2) for i, j in enumerate(order[:k]) if j in relevant)
    idcg = sum(1 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / idcg if idcg else 0.0


def evaluate(order, gabarito, k=10):
    """Top-k of a ranking, plus precision, recall and nDCG when there is a gabarito."""
    result = {"top10": order[:k]}
    if gabarito:
        relevant = gabarito["relevant"]
        hits = sum(1 for j in order[:k] if j in relevant)
        result[f"precision_at_{k}"] = round(hits / k, 3)
        result[f"recall_at_{k}"] = round(hits / len(relevant), 3)
        result[f"ndcg_at_{k}"] = round(ndcg_at(order, relevant, k), 3)
        result[f"obvious_irrelevant_in_top{k}"] = sum(
            1 for j in order[:k] if j in gabarito["obvious_irrelevant"]
        )
    return result


def load_gabarito(path):
    """Gabarito written by a person, or None when no file is given."""
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        "origin": str(path),
        "relevant": set(data["relevantes"]),
        "obvious_irrelevant": set(data.get("irrelevantes_obvias", [])),
    }


# --- pgvector ---------------------------------------------------------------------------------


def connect():
    load_dotenv()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is not set (copy .env.example to .env)")
    conn = psycopg.connect(url, autocommit=True)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def load_jobs_table(conn, jobs, job_vecs):
    dim = job_vecs.shape[1]
    conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
    conn.execute(
        f"CREATE TABLE {TABLE} (id integer PRIMARY KEY, title text NOT NULL, "
        f"embedding vector({dim}) NOT NULL)"
    )
    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO {TABLE} (id, title, embedding) VALUES (%s, %s, %s)",
            [
                (j["id"], j["title"], v.astype(np.float32))
                for j, v in zip(jobs, job_vecs, strict=True)
            ],
        )
    conn.execute(f"CREATE INDEX {TABLE}_hnsw ON {TABLE} USING hnsw (embedding vector_cosine_ops)")
    conn.execute(f"ANALYZE {TABLE}")


def ann_top(conn, vec, n):
    """Top-n jobs by cosine similarity (1 - distance) through the pgvector operator."""
    vec = vec.astype(np.float32)
    rows = conn.execute(
        f"SELECT id, 1 - (embedding <=> %s) FROM {TABLE} ORDER BY embedding <=> %s, id LIMIT %s",
        (vec, vec, n),
    ).fetchall()
    return {job_id: float(sim) for job_id, sim in rows}


def pool_sims(conn, vec, ids):
    """Cosine similarity of one vector against the given job ids."""
    rows = conn.execute(
        f"SELECT id, 1 - (embedding <=> %s) FROM {TABLE} WHERE id = ANY(%s)",
        (vec.astype(np.float32), list(ids)),
    ).fetchall()
    return {job_id: float(sim) for job_id, sim in rows}


def explain(conn, vec, n, force_index):
    """First plan nodes of the retrieval query; optionally with sequential scans disabled."""
    if force_index:
        conn.execute("SET enable_seqscan = off")
    rows = conn.execute(
        f"EXPLAIN SELECT id FROM {TABLE} ORDER BY embedding <=> %s LIMIT %s",
        (vec.astype(np.float32), n),
    ).fetchall()
    conn.execute("RESET enable_seqscan")
    plan = [r[0].strip() for r in rows[:3]]
    return {"uses_hnsw_index": any("hnsw" in line.lower() for line in plan), "plan": plan}


def pgvector_retrieval(conn, chunk_vecs, plain_resume_vec, requirement_vecs, job_ids, top_n):
    """Per-chunk top-n queries merged into a pool, then re-scored. Returns scores per strategy.

    Why per-chunk queries: a job's maximum chunk cosine (strategy A) is never worse ranked inside
    its best chunk's list than overall, so the union of the per-chunk top-n lists contains the
    overall top-n of A exactly. B and C re-score that same pool with the chunk x job similarities
    fetched from pgvector (C uses requirement vectors held in memory).
    """
    index = {job_id: i for i, job_id in enumerate(job_ids)}
    pool = set()
    for vec in chunk_vecs:
        pool |= set(ann_top(conn, vec, top_n))
    pool_ids = sorted(pool)
    per_chunk = [pool_sims(conn, vec, pool_ids) for vec in chunk_vecs]
    sims = np.array([[row[j] for j in pool_ids] for row in per_chunk])
    score_a = aggregate_a(sims)
    pooled = {
        "A": dict(zip(pool_ids, score_a, strict=True)),
        "B": dict(zip(pool_ids, aggregate_b(sims), strict=True)),
        "C": {
            j: coverage_c(chunk_vecs, requirement_vecs[index[j]], score_a[k])
            for k, j in enumerate(pool_ids)
        },
    }
    mean_vec = normalize(chunk_vecs).mean(axis=0)
    scores = {
        "baseline": ann_top(conn, plain_resume_vec[0], top_n),
        **pooled,
        "D": ann_top(conn, mean_vec, top_n),
    }
    return scores, pool_ids, sims


def order_of(score_by_id):
    return sorted(score_by_id, key=lambda j: (-score_by_id[j], j))


# --- Benchmark --------------------------------------------------------------------------------


def run_benchmark(args):
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    jobs = data["jobs"]
    job_ids = [j["id"] for j in jobs]
    gabarito = load_gabarito(args.gabarito)
    query_prefix, passage_prefix = prefixes_for(args.model)
    job_texts = [build_job_text(j) for j in jobs]
    chunks = build_resume_chunks(data["resume"])
    whole_text = whole_resume_text(data["resume"])
    plain_resume_text = query_prefix + whole_text
    requirements = [split_requirements(j["description"]) for j in jobs]
    flat_requirements = [passage_prefix + r for reqs in requirements for r in reqs]

    print(f"Model: {args.model}\nInput: {args.input} ({len(jobs)} jobs, {len(chunks)} chunks)")

    # 1. Load: time and memory.
    cached = model_in_cache(args.model)
    memory_before = rss_mb()
    start = time.perf_counter()
    model = SentenceTransformer(args.model, device="cpu")
    load_seconds = time.perf_counter() - start
    memory_after_load = rss_mb()
    model.encode(["warm-up"], convert_to_numpy=True)  # first call is slower; excluded
    limit = int(model.max_seq_length)
    tokenizer = model.tokenizer
    print(f"Load: {load_seconds:.2f}s (cached: {cached}), max_seq_length {limit}")

    # 2. Tokens: does every chunk and job fit the model?
    chunk_tokens = token_counts(tokenizer, chunks, query_prefix)
    job_tokens = token_counts(tokenizer, job_texts, passage_prefix)
    plain_tokens = token_counts(tokenizer, [whole_text], query_prefix)[0]
    tokens = {
        "max_seq_length": limit,
        "whole_resume_tokens": plain_tokens,
        "whole_resume_truncated": plain_tokens > limit,
        "chunk_tokens": chunk_tokens,
        "chunks_over_limit": sum(1 for t in chunk_tokens if t > limit),
        "max_job_tokens": max(job_tokens),
        "jobs_over_limit": sum(1 for t in job_tokens if t > limit),
        "requirements_total": len(flat_requirements),
    }
    print(
        f"Tokens: whole resume {plain_tokens} (limit {limit}), chunks {chunk_tokens}, "
        f"longest job {tokens['max_job_tokens']}, over limit: "
        f"{tokens['chunks_over_limit']} chunks, {tokens['jobs_over_limit']} jobs"
    )
    if tokens["chunks_over_limit"] or tokens["jobs_over_limit"]:
        print("WARNING: some texts exceed the model limit and will be truncated")

    # 3. Embeddings and generation time (chunks and jobs in one batch each).
    def encode(texts):
        return model.encode(texts, batch_size=BATCH_SIZE, convert_to_numpy=True)

    chunk_inputs = [query_prefix + c for c in chunks]
    job_inputs = [passage_prefix + t for t in job_texts]
    timing = {
        "runs": args.runs,
        "resume_whole_truncated": time_runs(lambda: encode([plain_resume_text]), args.runs),
        "resume_chunks_batch": time_runs(lambda: encode(chunk_inputs), args.runs),
        "jobs_batch": time_runs(lambda: encode(job_inputs), args.runs),
        "requirements_batch": time_runs(lambda: encode(flat_requirements), args.runs),
    }
    chunk_vecs = encode(chunk_inputs)
    plain_resume_vec = encode([plain_resume_text])
    job_vecs = encode(job_inputs)
    flat_vecs = encode(flat_requirements)
    requirement_vecs, cursor = [], 0
    for reqs in requirements:
        requirement_vecs.append(flat_vecs[cursor : cursor + len(reqs)])
        cursor += len(reqs)
    peak = rss_mb()
    print(
        f"Generation (median of {args.runs}): whole resume "
        f"{timing['resume_whole_truncated']['median_ms']} ms | {len(chunks)} chunks "
        f"{timing['resume_chunks_batch']['median_ms']} ms | {len(jobs)} jobs "
        f"{timing['jobs_batch']['median_ms']} ms"
    )

    # 4. PT/EN support (same pairs as embedding_benchmark.py).
    equivalent = pair_similarities(model, PAIRS_EQUIVALENT, query_prefix)
    different = pair_similarities(model, PAIRS_DIFFERENT, query_prefix)
    pt_en = {
        "equivalent_mean": round(statistics.mean(equivalent), 4),
        "different_mean": round(statistics.mean(different), 4),
        "gap": round(statistics.mean(equivalent) - statistics.mean(different), 4),
    }

    # 5. Strategies with numpy over all jobs (reference ranking).
    reference = numpy_scores(chunk_vecs, plain_resume_vec, job_vecs, requirement_vecs)
    numpy_orders = {name: rank(job_ids, reference[name]) for name in STRATEGIES}
    strategies = {name: evaluate(numpy_orders[name], gabarito) for name in STRATEGIES}

    # 6. pgvector: store the jobs, retrieve per chunk, compare with the numpy ranking.
    conn = connect()
    try:
        server = conn.execute("SELECT version()").fetchone()[0]
        pgvector_version = conn.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()[0]
        load_jobs_table(conn, jobs, job_vecs)
        scores, pool_ids, chunk_pool_sims = pgvector_retrieval(
            conn, chunk_vecs, plain_resume_vec, requirement_vecs, job_ids, args.top_n
        )
        pg_orders = {name: order_of(scores[name]) for name in STRATEGIES}
        # Largest gap between a pgvector similarity and the numpy cosine for the same pair.
        column = {j: i for i, j in enumerate(job_ids)}
        numpy_pool = cosine_matrix(chunk_vecs, job_vecs)[:, [column[j] for j in pool_ids]]
        max_diff = float(np.abs(numpy_pool - chunk_pool_sims).max())
        match = {
            name: {
                "top10_identical": pg_orders[name][:10] == numpy_orders[name][:10],
                "top10_overlap": len(set(pg_orders[name][:10]) & set(numpy_orders[name][:10])),
            }
            for name in STRATEGIES
        }
        query_timing = {
            "top_n": args.top_n,
            "pool_size": len(pool_ids),
            "per_chunk_ann_queries": time_runs(
                lambda: [ann_top(conn, v, args.top_n) for v in chunk_vecs], args.runs
            ),
            "single_query_mean_vector": time_runs(
                lambda: ann_top(conn, normalize(chunk_vecs).mean(axis=0), args.top_n), args.runs
            ),
        }
        plan = {
            "default": explain(conn, chunk_vecs[0], args.top_n, force_index=False),
            "seqscan_off": explain(conn, chunk_vecs[0], args.top_n, force_index=True),
        }
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {TABLE}")
        conn.close()

    print(
        f"\npgvector {pgvector_version} | pool of {len(pool_ids)} jobs | "
        f"max |cosine diff vs numpy| {max_diff:.2e}"
    )
    header = f"{'strategy':<9}" + (f"{'P@10':>6}{'R@10':>7}{'nDCG@10':>9}" if gabarito else "")
    print(f"{header}  {'pgvector top10':<22}top 10 job ids")
    for name in STRATEGIES:
        s_, m = strategies[name], match[name]
        quality = ""
        if gabarito:
            quality = f"{s_['precision_at_10']:>6}{s_['recall_at_10']:>7}{s_['ndcg_at_10']:>9}"
        same = "identical" if m["top10_identical"] else f"{m['top10_overlap']}/10 in common"
        print(f"{name:<9}{quality}  {same:<22}{s_['top10']}")
    if not gabarito:
        print("Quality metrics skipped: no --gabarito given")

    return {
        "model": args.model,
        "input_file": str(args.input),
        "gabarito": gabarito
        and {
            "origin": gabarito["origin"],
            "relevant": sorted(gabarito["relevant"]),
            "obvious_irrelevant": sorted(gabarito["obvious_irrelevant"]),
        },
        "runtime_requirements": {
            **environment(),
            "postgres": server.split(",")[0],
            "pgvector": pgvector_version,
            "psycopg": package_version("psycopg"),
        },
        "model_info": {
            "max_seq_length": limit,
            "dimension": int(job_vecs.shape[1]),
            "cached_before_load": cached,
        },
        "load_seconds": round(load_seconds, 3),
        "memory_test": {
            "before_load_mb": round(memory_before, 1),
            "after_load_mb": round(memory_after_load, 1),
            "model_delta_mb": round(memory_after_load - memory_before, 1),
            "peak_mb": round(peak, 1),
        },
        "generation_time_test": timing,
        "similarity_test": {"pt_en": pt_en, "strategies": strategies},
        "chunking": {"chunks": chunks, "tokens": tokens},
        "pgvector_test": {
            "query_timing": query_timing,
            "plan": plan,
            "max_abs_cosine_diff_vs_numpy": max_diff,
            "match_with_numpy": match,
        },
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Structured chunking + pgvector benchmark.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Hugging Face model name")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="input JSON file")
    parser.add_argument(
        "--gabarito", type=Path, help="gabarito JSON written by a person (optional)"
    )
    parser.add_argument("--runs", type=int, default=5, help="timing repetitions (median)")
    parser.add_argument("--top-n", type=int, default=20, help="jobs per pgvector query")
    parser.add_argument("--output", type=Path, help="result JSON path (default: auto-named)")
    return parser.parse_args()


def main():
    args = parse_args()
    result = run_benchmark(args)
    slug = args.model.replace("/", "_")
    output = args.output or Path.cwd() / f"benchmark_chunking_{slug}_{Path(args.input).stem}.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResult written to: {output}")


if __name__ == "__main__":
    main()
