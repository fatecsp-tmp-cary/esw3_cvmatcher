# pgvector local validation

Issue: #24 (parent #4). Script: [`scripts/validate_pgvector.sql`](../../scripts/validate_pgvector.sql).

## How to reproduce

```bash
cp .env.example .env && docker compose up -d     # pgvector/pgvector:pg17
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/validate_pgvector.sql
```

The script creates and drops its own table (`pgvector_validation`) and exits non-zero if any
assertion fails.

## Required configuration

| Item | Value |
|---|---|
| Extension | `CREATE EXTENSION IF NOT EXISTS vector;` (needs a role allowed to create extensions; the compose superuser is) |
| Column | `embedding vector(384)`; the dimension must equal the embedding model's output (384 for all-MiniLM-L6-v2, paraphrase-multilingual-MiniLM-L12-v2 and multilingual-e5-small) |
| Nullable | `NULL` is accepted, matching PLAN.md (`embedding = NULL` means missing/invalid for the configured model) |
| Operators | `<=>` cosine distance (similarity = `1 - distance`), `<->` L2, `<#>` negative inner product |
| Indexes | `hnsw (embedding vector_cosine_ops)` and `ivfflat (embedding vector_cosine_ops) WITH (lists = N)` both build and are chosen by the planner |
| Dimension check | inserting a vector with the wrong dimension fails (`expected 384 dimensions, not 3`) |

Caveats found while validating:

- An ANN index is only used when the query vector is a constant or bind parameter. Ordering by a
  distance to a column of a joined table falls back to a sequential scan.
- On a table this small the planner prefers a sequential scan, so the index check forces
  `enable_seqscan = off`. Index choice and recall must be re-checked with the real job volume.
- IVFFlat needs data present before `CREATE INDEX` and a `lists` value sized to the row count; HNSW
  does not. Neither was tuned here.

## Result

| Step | Result |
|---|---|
| Enable extension | OK |
| `vector(384)` column, 30 rows | OK |
| Cosine / L2 / inner-product queries | OK; top-10 neighbours of a backend-like query are all in the backend cluster |
| HNSW and IVFFlat indexes | OK; planner uses each when forced |
| Dimension mismatch rejected | OK |
| NULL embedding stored | OK |

Run against pgvector/pgvector:pg17 (docker compose): PostgreSQL 17.11, pgvector 0.8.7. All steps OK. A previous dry run on PostgreSQL 16.14 with pgvector 0.6.0 gave the same results.

## Limits of this validation

- Vectors are deterministic synthetic ones, not model embeddings. It proves storage, operators and
  indexes, not retrieval quality. Quality is covered by the model benchmarks under #25.
- No performance or recall measurement at realistic volume.