# Architecture overview

The intended system separates API, candidate/job schemas, normalization,
source adapters and ingestion, persistence, indexing, and matching/ranking.
Matching is independent from ingestion; source adapters map external payloads to
the canonical job model. Current source layout is smaller than this target;
implementation status is tracked in the [MVP tasks](../../specs/feature-001-mvp/tasks.md).

```text
Structured CV → API/schema → transient candidate normalization ────┐
                                                                   ├→ matching → ranked response
Sources → ingestion → normalization → PostgreSQL jobs → FTS/vector ┘
```

PostgreSQL is the sole application-state store, including polling state and
worker coordination. A lightweight scheduler/worker may be bundled or separate;
no dedicated queue is required. Job embeddings are persisted; candidate
embeddings and match results are request-scoped. The local embedding model is a
deployment/cache artifact. Docker Compose with PostgreSQL + pgvector is the
reference local environment.

The intended canonical `Job` has exactly these fields:

```text
id, platform, source_job_id, source_expires_at, company, title, description,
keywords, skills, location, work_arrangement, seniority_level, salary, currency,
publication_date, first_seen_at, last_seen_at, last_verified_at, status,
job_url, raw, embedding, content_hash
```

`platform + source_job_id` is intended as source identity. Additional persisted
data belongs in separate structures. See [invariants](invariants.md), [ADR
index](decisions/README.md), and [MVP spec](../../specs/feature-001-mvp/spec.md).
