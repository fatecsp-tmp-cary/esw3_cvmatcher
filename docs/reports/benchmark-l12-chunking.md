# Resume chunking and pgvector retrieval benchmark

Issue: #25 (subtask #57; also covers the `multilingual-e5-small` question raised there).
Script: [`scripts/benchmarks/benchmark_l12_chunking.py`](../../scripts/benchmarks/benchmark_l12_chunking.py),
built on [`embedding_benchmark.py`](../../scripts/benchmarks/embedding_benchmark.py).

This report does **not** compare ranking quality. The shared input has no relevance labels, and the
only labels that existed were written by an AI and were removed. Quality metrics are opt-in through
`--gabarito`, with a file written by a person (see "What is still open").

## How to reproduce

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only first
pip install -e . --group benchmark
cp .env.example .env && docker compose up -d postgres
cd /tmp   # the result JSON is written to the current directory
python <repo>/scripts/benchmarks/benchmark_l12_chunking.py --runs 3
python <repo>/scripts/benchmarks/benchmark_l12_chunking.py --model intfloat/multilingual-e5-small
python <repo>/scripts/benchmarks/benchmark_l12_chunking.py --gabarito my_gabarito.json
```

The script stores the jobs in its own table (`vagas_pgvector_validation`) and drops it at the end.
It does not touch anything else in the database.

## Environment

| Item | Value |
|---|---|
| OS / CPU / RAM | Linux 7.0.0-31-generic x86_64, Intel Core i7-1185G7 (4 cores / 8 threads), 38.9 GB |
| Power | AC power, no other heavy process running |
| Python / PyTorch / sentence-transformers | 3.12.3 / 2.14.1+cpu / 6.1.0 |
| PostgreSQL / pgvector / psycopg | 17.11 / 0.8.7 / 3.3.6 (`pgvector/pgvector:pg17` from `docker-compose.yml`) |
| Models | `paraphrase-multilingual-MiniLM-L12-v2` (128 tokens, 384 dims, no prefixes), `intfloat/multilingual-e5-small` (512 tokens, 384 dims, `query: ` / `passage: ` prefixes) |

## Method

- **Jobs:** one embedding per job from `title. description`, stored in a `vector(384)` column with
  an HNSW index (`vector_cosine_ops`). Similarity is reported as `1 - cosine distance`.
- **Resume chunks, by structure:** chunk 0 is `title. skills`, then one chunk per item of
  `experience`. Every chunk is embedded in one batch.
- **Strategies**, all computed from the chunk vectors and the job vector:
  - `baseline`: the whole resume as one text, truncated by the model to its limit (no chunking).
  - `A`: maximum cosine over the chunks.
  - `B`: mean of the 3 highest chunk cosines.
  - `C`: requirement coverage. The job description is split on commas, semicolons and periods
    into requirements (2 to 5 per job for 98 of 100 jobs). For each requirement the most similar
    chunk is taken, and the scores are averaged.
  - `D`: one cosine against the mean of the chunk vectors (a single pgvector query).

### How pgvector is queried

A resume has several chunks, so the retrieval uses one query per chunk and merges in Python:

1. For each chunk, ask pgvector for its top-N jobs (`ORDER BY embedding <=> $chunk LIMIT N`, with
   N = 20). The union of the lists is the candidate pool.
2. For each chunk, fetch its similarity to every pool job (`WHERE id = ANY(...)`), then aggregate
   with `A`, `B` or `C` in Python.

Why this and not the mean vector (`D`):

- The union of the per-chunk top-N lists contains the overall top-N of `A` exactly: a job with the
  A-score `s` can only rank at or above its overall position inside the list of the chunk that gave
  it `s`.
- It supports `A`, `B` and `C`, which need the similarity of each chunk to each job. The mean vector
  collapses the chunks before the search.
- The cost is negligible: 10 chunk queries take about 6.6 ms in total, against about 270 ms to
  embed the chunks.
- The query vector is a bind parameter, which is what lets the planner use the ANN index (see
  `pgvector-validation.md`).

## Results (versioned input, 1 resume and 100 jobs)

### Token budget

| | L12 | e5-small |
|---|---|---|
| Whole resume (tokens, with special tokens) | 368 | 371 |
| Model limit | 128 | 512 |
| Resume chunks / largest chunk | 10 / 65 | 10 / 68 |
| Longest job | 116 | 118 |
| Chunks or jobs over the limit | 0 | 0 |

Structural chunking removes truncation entirely for L12: no chunk and no job exceeds 128 tokens.
Without chunking, L12 reads only the first 128 of the 368 resume tokens. e5-small reads the whole
resume.

### pgvector against numpy

- On this input, the top 10 returned through pgvector is identical to the numpy ranking over all
  jobs for every strategy and both models (10 of 10 cases).
- Checked also on three local inputs that are not versioned: 27 of 30 cases identical. The 3
  differences are all strategy `C`, which is re-scored only on the pool, so a job outside the pool
  cannot enter.
- Largest difference between a pgvector similarity and the numpy cosine: 2.6e-07 (float32).
- The default plan on 100 rows is a sequential scan plus sort. With `enable_seqscan = off` the
  planner uses `vagas_pgvector_validation_hnsw`, as in `pgvector-validation.md`.

### Resources (median of 3 runs, AC power)

| | L12 | e5-small |
|---|---|---|
| Load time | 6.0 s | 7.5 s |
| Memory delta / peak (RSS) | 592 MB / 1203 MB | 455 MB / 1259 MB |
| Whole resume, plain encode | 75 ms | 202 ms |
| 10 resume chunks, one batch | 268 ms | 287 ms |
| 100 jobs, one batch | 2705 ms | 2930 ms |
| 326 job requirements (only for `C`) | 2117 ms | 2328 ms |
| 10 per-chunk pgvector queries / 1 mean-vector query | 6.6 ms / 0.7 ms | 6.8 ms / 1.0 ms |

Load time includes Hugging Face Hub network checks even when the model is cached.

## Findings

1. **Chunking by structure fits the model.** Every chunk and job is well under 128 tokens, so no
   text is truncated. This is not a statement about ranking quality.
2. **L12 needs chunking for a realistic resume, e5-small does not.** The 368-token resume is cut to
   128 tokens by L12 without chunking; e5-small reads it whole. That removes the chunking code and
   the per-chunk queries, at the price of the `query: ` / `passage: ` prefixes and a slower plain
   encode of the resume (202 ms against 75 ms).
3. **The pgvector retrieval is equivalent to the numpy computation.** The per-chunk top-N design
   returns the same top 10, and the cost of the queries is negligible next to embedding.
4. **`C` costs an extra 2 seconds of embeddings per 100 jobs** (the requirements), which makes it
   the most expensive strategy to run.
5. Both models output 384 dimensions, so the `vector(384)` column from #24 works for either.

## What is still open

- **Ranking quality was not compared.** Choosing between L12 and e5-small, or between `baseline`,
  `A`, `B`, `C` and `D`, needs a gabarito written by a person: for each resume, the jobs that must
  be in the top 10. Pass it with `--gabarito` (`{"relevantes": [ids], "irrelevantes_obvias": [ids]}`)
  to get precision@10, recall@10 and nDCG@10 per strategy.
- A single resume is not enough to separate strategies or models; use several, ideally anonymized
  real ones.
- The input uses `experience` as plain strings. The `CandidateProfile` schema (#84) uses objects;
  the script builds their text from `title`, `company`, `description` and `skills`, but this path
  has not been exercised with real parser output.
- Retrieval ran on 100 rows, where the planner does not need the ANN index. Index choice, recall and
  latency at a realistic job volume are not measured.
- Timings come from one machine and are meant for comparing models on that machine only.

## Recommendation

- **Retrieval:** per-chunk top-N queries (N = 20) merged in Python, then re-score the pool.
- **Model and aggregation:** not decided here. Mechanically, e5-small avoids chunking for resumes up
  to 512 tokens and L12 does not; whether either ranks better is unknown until there is a gabarito
  written by a person. The choice belongs to #26.
