# ADR-025: Initial matching stack

- **Status:** Accepted (records the technology choices already implemented on `main`; calibration, release approval and ADR-022 remain pending)
- **Date:** 2026-11-16
- **Issue:** #26 (parent #4)
- **Authority:** [MVP spec](../../../specs/feature-001-mvp/spec.md), [ADR-004](ADR-004-portuguese-full-text-search.md), [ADR-005](ADR-005-weighted-any-term-fts.md), [ADR-022](ADR-022-bilingual-ascii-search-and-fuzzy-fallback.md) and the benchmark reports under [`docs/match/benchmarks/`](../../match/benchmarks/).

This record gathers the selected search, vector and embedding technologies in one
place. It adds no new technical decision; the detailed policies stay in the ADRs and
documents linked below.

## Context

The match team needed local tools for textual search, vector search and embeddings
that work with PostgreSQL on CPU, with no paid embedding API or mandatory
proprietary service (issue #4).

## Decision

| Concern | Selected | Where it is defined |
|---|---|---|
| Textual search | PostgreSQL full-text search, `portuguese` configuration, any-term queries, weights A/B/D | ADR-004, ADR-005, [textual retrieval](../../match/textual-retrieval.md) |
| Vector storage and search | pgvector in the pinned PostgreSQL 17 image, `vector(384)`, cosine distance (`<=>`) | [pgvector validation](../../match/pgvector-validation.md) |
| Embedding model | `intfloat/multilingual-e5-small`, pinned revision, 384 dimensions, CPU, `query: ` / `passage: ` prefixes, local files only | [local embeddings](../../match/local-embeddings.md) |
| Candidate representation | Resume split by structure into chunks; semantic score from the mean of the 3 highest chunk similarities | [benchmark](../../match/benchmarks/benchmark-l12-chunking.md), [scoring policy](../../match/scoring-policy.md) |
| Candidate data | Embedded in memory per request; only job embeddings are persisted | [invariants](../invariants.md) |

No paid or hosted inference is used. Typing-error tolerance is a separate bounded
policy (ADR-022); no fuzzy library is part of this stack.

## Alternatives considered

Measured on 5 fictitious resumes and 100 fictitious jobs with a human gabarito
(mean nDCG@10, chunked resume, strategy B; details in the benchmark report):

- `paraphrase-multilingual-MiniLM-L12-v2`: 0.634. Supports PT/EN (PT-EN similarity gap
  0.82) but its 128-token limit forces chunking, and chunking changed about half of
  its top 10 in the single-resume test.
- `all-MiniLM-L6-v2`: not recommended. Weak PT/EN support (gap 0.16) and a 256-token
  limit; kept only as a baseline.
- `multilingual-e5-small`: 0.698. Selected: higher mean with chunking, pool
  recall close to L12 (0.94 against 0.96), 512-token limit, same 384 dimensions. The cost is that the two
  prefixes must be applied by one shared function in the worker and in the API.
- Whole resume as one vector: 0.621 (e5-small) and 0.629 (L12) because the model
  truncates it; chunking is needed for real resumes.
- Per-requirement coverage and a mean-vector query scored lower and were rejected.
- Hosted embedding APIs: excluded by the constraint of no paid or mandatory
  proprietary service.

## Local setup

- PostgreSQL with pgvector: `docker compose up -d` and
  `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/helpers/validate_pgvector.sql`
  ([pgvector validation](../../match/pgvector-validation.md)).
- Pinned model preparation, API, worker and migrations: the
  [deployment procedure](../../operations/deployment.md) (`model-init`,
  `prepare-extraction`, `prepare-embeddings`, then `up`).
- Reproducing the benchmark: [benchmark report](../../match/benchmarks/benchmark-l12-chunking.md).

## Limitations

- The evidence is small: 5 resumes, one person writing the gabarito, fictitious jobs
  and 7 to 11 relevant jobs per resume. Differences below about 0.05 nDCG@10 are not
  reliable, so e5-small and L12 are close, and e5-small does not lose quality here.
- The gabarito was corrected after a first pass partly because of jobs both models
  ranked in the top 10, so it is not fully independent of the rankings.
- The benchmark embeds jobs as `title. description`, not the full job representation
  of the spec, and ran on 100 rows where the planner needs no ANN index. No migration
  creates an HNSW or IVFFlat index: semantic search is an exact cosine scan. Index
  choice, recall and latency at realistic volume are not measured.
- Similarity calibration and compatibility weights are provisional
  ([scoring policy](../../match/scoring-policy.md)); empirical calibration and
  release approval remain pending.
- Mixed or generic profiles score lower for every strategy and model.
- Timings come from one machine and compare models only on that machine.
- Portuguese stemming does not give English stemming or guaranteed accent-insensitive
  matching (ADR-005); bilingual search is the accepted but unimplemented ADR-022.

## Consequences

Replacing the embedding model needs a new revision, a re-embedding of all jobs and a
recalibration of the similarity policy. Changing the full-text configuration or
weights needs an index migration and a ranking review (ADR-005).
