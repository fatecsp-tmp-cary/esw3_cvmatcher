# Resume chunking and pgvector retrieval benchmark

Issue: #25 (subtask #57; also answers the `multilingual-e5-small` question raised there).
Script: [`scripts/benchmarks/benchmark_l12_chunking.py`](../../scripts/benchmarks/benchmark_l12_chunking.py),
built on [`embedding_benchmark.py`](../../scripts/benchmarks/embedding_benchmark.py).

## How to reproduce

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only first
pip install -e . --group benchmark
cp .env.example .env && docker compose up -d postgres
cd /tmp   # the result JSON is written to the current directory
python <repo>/scripts/benchmarks/benchmark_l12_chunking.py --runs 3
python <repo>/scripts/benchmarks/benchmark_l12_chunking.py --model intfloat/multilingual-e5-small
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
- **Ground truth:** relevant jobs are those labeled `fit` 2 in the input, obvious irrelevant ones
  are `fit` -1. nDCG@10 uses gains 3, 1, 0, 0 for `fit` 2, 1, 0, -1. **The labels were written by an
  AI and no human has reviewed them** (`scripts/benchmarks/gabarito_curriculo_vagas.json` is marked
  `revisar_humano: true`).

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
- It keeps the strategies that perform best (`A`, `B`). The mean vector needs a single query but
  scored lower on most inputs.
- The cost is negligible: 10 chunk queries take about 6.6 ms in total, against about 270 ms to
  embed the chunks.
- The query vector is a bind parameter, which is what lets the planner use the ANN index (see
  `pgvector-validation.md`).

## Results

### Token budget

| Input | Whole resume (tokens) | Limit | Chunks | Largest chunk | Longest job |
|---|---|---|---|---|---|
| v2 (versioned) | 368 | 128 | 10 | 65 | 116 |
| v3 (local) | 251 | 128 | 9 | 41 | 116 |
| v4 (local) | 32 | 128 | 3 | 18 | 116 |
| v5 (local) | 243 | 128 | 8 | 45 | 116 |

Token counts are for L12 and include the 2 special tokens. **No chunk and no job exceeded 128
tokens**, so structural chunking removes truncation entirely. The whole resume exceeds the L12 limit
in 3 of the 4 inputs. With e5-small (512 tokens) the whole resume fits in every input (371 tokens
at most).

### Ranking quality (nDCG@10; 1 resume per input, 100 jobs each)

L12:

| Input | baseline | A | B | C | D |
|---|---|---|---|---|---|
| v2 | 0.880 | 1.000 | 0.958 | 0.824 | 0.813 |
| v3 | 0.936 | 0.788 | 0.958 | 0.546 | 0.398 |
| v4 | 0.894 | 0.859 | 0.829 | 0.821 | 0.829 |
| v5 | 0.598 | 0.587 | 0.559 | 0.560 | 0.588 |
| **Mean** | **0.827** | 0.808 | 0.826 | 0.688 | 0.657 |

e5-small (here `baseline` is the untruncated whole resume):

| Input | baseline | A | B | C | D |
|---|---|---|---|---|---|
| v2 | 0.909 | 0.954 | 0.943 | 0.867 | 0.715 |
| v3 | 0.882 | 0.726 | 0.937 | 0.774 | 0.639 |
| v4 | 0.831 | 0.899 | 0.850 | 0.561 | 0.850 |
| v5 | 0.639 | 0.781 | 0.702 | 0.598 | 0.718 |
| **Mean** | 0.815 | 0.840 | **0.858** | 0.700 | 0.730 |

Mean precision@10 / recall@10 / non-fit jobs (`fit` <= 0) in the top 20:

| | baseline | A | B | C | D |
|---|---|---|---|---|---|
| L12 | 0.70 / 0.57 / 4.5 | 0.70 / 0.57 / 7.2 | 0.68 / 0.52 / 6.0 | 0.50 / 0.40 / 7.0 | 0.50 / 0.43 / 7.2 |
| e5-small | 0.63 / 0.48 / 2.2 | 0.68 / 0.58 / 2.2 | 0.70 / 0.57 / 2.5 | 0.48 / 0.42 / 4.0 | 0.50 / 0.43 / 3.5 |

Recall@10 is capped at 0.67 for v2, v3 and v4 (10 slots for 15 relevant jobs), and at 1.0 for v5
(5 relevant jobs).

### pgvector against numpy

- The top 10 returned through pgvector is identical to the numpy ranking over all jobs in 37 of 40
  cases (2 models x 4 inputs x 5 strategies).
- The 3 differences are all strategy `C` (9 of 10 in common). They are expected: `C` is re-scored
  only on the pool, so a job outside the pool cannot enter.
- Largest difference between a pgvector similarity and the numpy cosine: 2.6e-07 (float32).
- Default plan on 100 rows is a sequential scan plus sort. With `enable_seqscan = off` the planner
  uses `vagas_pgvector_validation_hnsw`, as in `pgvector-validation.md`.

### Resources (v2, 100 jobs, median of 3 runs)

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

1. **Chunking did not beat truncation for L12.** The mean nDCG@10 of the whole truncated resume
   (0.827) is the same as `B` (0.826) and above `A` (0.808). The first 128 tokens (title, skills and
   the first experience entries) already carry most of the signal in these resumes.
2. **`B` is the most stable aggregation.** `A` is the best on v2 (1.000) but drops on v3 for both
   models (0.788 and 0.726), because a single chunk that happens to match can lift an unrelated job.
3. **`C` and `D` are worse on average in both models** (0.66 to 0.73). `C` also costs an extra
   2 seconds of embeddings per 100 jobs. Not recommended.
4. **The model difference is small.** The best mean is 0.858 (e5-small, `B`) against 0.827 (L12,
   baseline or `B`). With 4 resumes this is not a clear difference. e5-small keeps fewer non-fit jobs
   in the top 20 (2.2 against 4.5 to 7.2).
5. **e5-small does not need chunking for these inputs**, since every whole resume is under 512
   tokens. That removes the chunking code and the per-chunk queries, at the price of a slower plain
   encode of the resume (202 ms against 75 ms) and the `query: ` / `passage: ` prefixes.
6. Both models output 384 dimensions, so the `vector(384)` column from #24 works for either.

## Limitations

- 4 resumes, one per input, and 100 fictitious jobs. Differences below about 0.05 in nDCG@10 are not
  reliable.
- The `fit` labels were written by an AI. Results are only as good as those labels; a human review
  is pending.
- Only v2 is versioned in the repository. v3, v4 and v5 are local files; the cross-input tables above
  cannot be reproduced from the repository alone.
- The inputs use `experience` as plain strings. The `CandidateProfile` schema (#84) uses objects;
  the script builds their text from `title`, `company`, `description` and `skills`, but this path has
  not been exercised with real parser output.
- Retrieval runs on 100 rows, where the planner does not need the ANN index. Index choice, recall and
  latency at a realistic job volume are not measured.
- Timings come from one machine and are meant for comparing models on that machine only.

## Recommendation

- **Retrieval:** per-chunk top-N queries (N = 20) merged in Python, then re-score the pool.
- **Aggregation:** if chunking is used, take `B` (mean of the 3 highest chunk cosines). Do not use
  `C` or `D`.
- **Model:** this benchmark does not separate L12 from e5-small. Because L12 needs chunking for
  realistic resumes and chunking did not improve the ranking, e5-small is the simpler choice if the
  decision in #26 confirms the result with reviewed labels and more resumes.
- **Before relying on these numbers:** review the `fit` labels, add resumes (anonymized real ones if
  possible) and version the extra inputs.
