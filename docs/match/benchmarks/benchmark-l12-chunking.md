# Resume chunking and pgvector retrieval benchmark

Issue: #25 (subtask #57; also covers the `multilingual-e5-small` question raised there).
Script: [`scripts/benchmarks/benchmark_l12_chunking.py`](../../scripts/benchmarks/benchmark_l12_chunking.py),
built on [`embedding_benchmark.py`](../../scripts/benchmarks/embedding_benchmark.py).
Inputs: `embedding_benchmark_input.json` (100 jobs and the `backend` resume),
`embedding_benchmark_resumes.json` (4 more resumes) and `embedding_benchmark_gabarito.json`
(relevant and obviously irrelevant jobs for each of the 5 resumes, written by a person).

## How to reproduce

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only first
pip install -e . --group benchmark
cp .env.example .env && docker compose up -d postgres
cd /tmp   # the result JSON is written to the current directory
B=<repo>/scripts/benchmarks
python $B/benchmark_l12_chunking.py --runs 3 \
    --resumes $B/embedding_benchmark_resumes.json --gabarito $B/embedding_benchmark_gabarito.json
python $B/benchmark_l12_chunking.py --model intfloat/multilingual-e5-small \
    --resumes $B/embedding_benchmark_resumes.json --gabarito $B/embedding_benchmark_gabarito.json
```

The script stores the jobs in its own table (`vagas_pgvector_validation`) and drops it at the end.
Resume vectors are never stored; the result JSON contains the text of the resume chunks, so use it
only with fictitious resumes (PLAN.md: candidate data is never persisted or logged).

## Environment

| Item | Value |
|---|---|
| OS / CPU / RAM | Linux 7.0.0-31-generic x86_64, Intel Core i7-1185G7 (4 cores / 8 threads), 38.9 GB |
| Python / PyTorch / sentence-transformers | 3.12.3 / 2.14.1+cpu / 6.1.0 |
| PostgreSQL / pgvector / psycopg | 17.11 / 0.8.7 / 3.3.6 (`pgvector/pgvector:pg17` from `docker-compose.yml`) |
| Models | `paraphrase-multilingual-MiniLM-L12-v2` (128 tokens, 384 dims, no prefixes), `intfloat/multilingual-e5-small` (512 tokens, 384 dims, `query: ` / `passage: ` prefixes) |

## Method

- **Jobs:** one embedding per job from `title. description`, stored in a `vector(384)` column with
  an HNSW index (`vector_cosine_ops`). Similarity is reported as `1 - cosine distance`.
- **Resume chunks, by structure:** chunk 0 is `title. skills`, then one chunk per item of
  `experience`. If the skill list does not fit the model, chunk 0 is split into several chunks that
  repeat the title. Every chunk is embedded in one batch.
- **Strategies**, all computed from the chunk vectors and the job vector:
  - `baseline`: the whole resume as one text, truncated by the model to its limit (no chunking).
  - `A`: maximum cosine over the chunks.
  - `B`: mean of the 3 highest chunk cosines.
  - `C`: requirement coverage. The job description is split on commas, semicolons and periods
    into requirements (2 to 5 per job for 98 of 100 jobs). For each requirement the most similar
    chunk is taken, and the scores are averaged.
  - `D`: one cosine against the mean of the chunk vectors (a single pgvector query).
- **Gabarito:** written by one person, per resume: the jobs that must be in the top 10 (7 to 11) and
  10 obviously irrelevant ones. Metrics: precision@10, recall@10, nDCG@10 with binary relevance, and
  **pool recall**, the share of relevant jobs among the candidates that pgvector retrieves (the
  measure that matters for a first retrieval phase).

### How pgvector is queried

A resume has several chunks, so the retrieval uses one query per chunk and merges in Python:

1. For each chunk, ask pgvector for its top-N jobs (`ORDER BY embedding <=> $chunk LIMIT N`, with
   N = 20). The union of the lists is the candidate pool.
2. For each chunk, fetch its similarity to every pool job (`WHERE id = ANY(...)`), then aggregate
   with `A`, `B` or `C` in Python.

- The union of the per-chunk top-N lists contains the overall top-N of `A` exactly: a job with the
  A-score `s` can only rank at or above its overall position inside the list of the chunk that gave
  it `s`.
- It supports `A`, `B` and `C`, which need the similarity of each chunk to each job. The mean vector
  collapses the chunks before the search.
- The query vector is a bind parameter, which is what lets the planner use the ANN index (see
  `pgvector-validation.md`).

## Results (5 resumes, the same 100 jobs)

### Token budget

| Resume | Whole resume (tokens, L12 / e5) | Chunks (L12 / e5) | Largest chunk (L12 / e5) |
|---|---|---|---|
| backend | 368 / 371 | 10 / 10 | 65 / 68 |
| devops_pleno | 621 / 624 | 14 / 13 | 117 / 144 |
| suporte_junior | 81 / 84 | 3 / 3 | 35 / 38 |
| fullstack_medio | 392 / 395 | 9 / 9 | 83 / 86 |
| dados_misto | 374 / 377 | 11 / 11 | 80 / 83 |

Limits: 128 tokens for L12, 512 for e5-small. No chunk and no job (longest: 116 and 118 tokens)
exceeds the limit. The skill list of `devops_pleno` alone needs 141 tokens, so for L12 chunk 0 is
split in two (117 and 36 tokens). Without chunking, L12 truncates 4 of the 5 resumes; e5-small
truncates only `devops_pleno`.

### Ranking quality

Mean over the 5 resumes (pool recall in parentheses):

| nDCG@10 | baseline | A | B | C | D |
|---|---|---|---|---|---|
| L12 | 0.629 (0.72) | 0.490 (0.96) | **0.634** (0.96) | 0.474 (0.96) | 0.573 (0.62) |
| e5-small | 0.621 (0.74) | **0.719** (0.94) | 0.698 (0.94) | 0.499 (0.94) | 0.531 (0.69) |

Mean precision@10: L12 0.54 / 0.42 / 0.52 / 0.42 / 0.44, e5-small 0.50 / 0.62 / 0.62 / 0.42 / 0.40
(baseline / A / B / C / D).

nDCG@10 per resume:

| L12 | baseline | A | B | C | D |
|---|---|---|---|---|---|
| backend | 0.857 | 0.870 | 0.870 | 0.542 | 0.681 |
| devops_pleno | 0.637 | 0.305 | 0.498 | 0.514 | 0.330 |
| suporte_junior | 0.715 | 0.779 | 0.860 | 0.533 | 0.860 |
| fullstack_medio | 0.706 | 0.298 | 0.425 | 0.510 | 0.425 |
| dados_misto | 0.229 | 0.198 | 0.519 | 0.273 | 0.567 |

| e5-small | baseline | A | B | C | D |
|---|---|---|---|---|---|
| backend | 0.727 | 0.931 | 0.915 | 0.612 | 0.573 |
| devops_pleno | 0.393 | 0.653 | 0.676 | 0.615 | 0.448 |
| suporte_junior | 0.658 | 0.658 | 0.716 | 0.554 | 0.716 |
| fullstack_medio | 0.773 | 0.668 | 0.753 | 0.608 | 0.330 |
| dados_misto | 0.555 | 0.684 | 0.429 | 0.106 | 0.586 |

### pgvector against numpy

- The top 10 returned through pgvector is identical to the numpy ranking over all jobs in 45 of 50
  cases (2 models x 5 resumes x 5 strategies). All 5 differences are strategy `C`, which is re-scored
  only on the pool, so a job outside the pool cannot enter.
- Largest difference between a pgvector similarity and the numpy cosine: 8.1e-07 (float32).
- The default plan on 100 rows is a sequential scan plus sort. With `enable_seqscan = off` the
  planner uses `vagas_pgvector_validation_hnsw`, as in `pgvector-validation.md`.

### Resources (backend resume, 100 jobs, median of 3 runs, AC power)

Measured with the earlier single-resume version of the script; load and memory do not depend on the
resume. Not repeated for the other resumes.

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

1. **One query per chunk brings back more relevant jobs.** The pool of the per-chunk queries holds
   94% to 96% of the relevant jobs on average, against 62% to 74% for a query with a single resume
   vector (`baseline` or `D`). For each model the pool is never smaller and is larger in 3 of the
   5 resumes (`devops_pleno`, `dados_misto` and one more).
2. **`B` is the most stable aggregation.** `A` has the best mean for e5-small (0.719) but one of the
   lowest for L12 (0.490; only `C` is lower). A single generic chunk (documentation, incident handling) can lift an unrelated
   job, which is the likely cause: with `devops_pleno`, `A` in L12 returns Coordenador de Projetos,
   Analista de Negócios and Gerente de Projetos. This was not checked chunk by chunk. `B` (0.634 and
   0.698) averages such chunks out.
3. **`C` is the weakest in both models** (0.47 and 0.50), and it costs an extra 2 seconds of
   embeddings per 100 jobs. `D` is in the middle on ranking but loses pool recall.
4. **With a single resume vector the two models tie** (0.629 and 0.621). The difference shows only
   when the resume is chunked: e5-small gains from `A` and `B`, L12 gains from `B` only, and only
   marginally over the baseline.
5. **Mixed and generic profiles are harder.** `dados_misto` (data engineering, BI and some
   development) has precision@10 between 0.1 and 0.4 for every strategy and both models.
   `suporte_junior`, although written vaguely, does well (nDCG@10 up to 0.86), probably because it
   is one clear area.
6. Both models output 384 dimensions, so the `vector(384)` column from #24 works for either.

## Limitations

- 5 resumes, one person writing the gabarito, and 7 to 11 relevant jobs per resume. Differences
  below about 0.05 in nDCG@10 are not reliable.
- **The gabarito is not fully independent of the rankings.** After a first pass, three corrections
  were made (`suporte_junior` 44 replaced by 47, 78 and 79 added; `devops_pleno` 49 and 63 added),
  prompted in part by jobs that both models had placed in the top 10.
- The jobs are fictitious and their areas have different depth (about 15 backend jobs, 2 for QA).
  Compare strategies and models within a resume, not resumes with each other.
- The jobs are embedded as `title. description`; PLAN.md also puts normalized skills, requirements,
  location and mode in the job representation. The candidate representation here uses title,
  skills and experience only.
- The semantic score was not normalized to the `[0, 100]` range that PLAN.md requires for the final
  score; only the ranking was evaluated.
- The inputs use `experience` as plain strings. The `CandidateProfile` schema (#84) uses objects;
  the script builds their text from `title`, `company`, `description` and `skills`, but this path
  has not been exercised with real parser output.
- Retrieval ran on 100 rows, where the planner does not need the ANN index. Index choice, recall and
  latency at a realistic job volume are not measured.
- Timings come from one machine and are meant for comparing models on that machine only.

## Credits

This benchmark builds on the work of @fabiola-girotti (#57), who found the 128-token truncation and
tested chunking, and @ricardosakugawa (#56), whose input format and all-MiniLM-L6-v2 results were
the starting point. Their own benchmarks are meant to be added under `scripts/benchmarks/` (one
folder per issue) and `docs/match/benchmarks/`; this report links to them once they are merged.

## Recommendation

- **Retrieval:** per-chunk top-N queries (N = 20) merged in Python, then re-score the pool. It is
  the retrieval phase that fits the PLAN.md pipeline, where the semantic stage runs next to the
  textual one.
- **Aggregation:** `B` (mean of the 3 highest chunk cosines) as the semantic score. It is the only
  one that is competitive in both models. Do not use `C`.
- **Model:** `multilingual-e5-small` has the better mean with chunking (0.70 against 0.63) and the
  same pool recall, at the price of the `query: ` / `passage: ` prefixes, which must be applied by
  one shared function in the worker and in the API. The evidence is limited (see above), so the
  decision belongs to #26.
