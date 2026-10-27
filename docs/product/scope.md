# Product scope

## In scope

- Structured CV validation and normalization.
- Modular multi-source job ingestion, with at least one source for MVP.
- Job normalization, source-specific identity, content-change detection,
  lifecycle management, and expiration.
- PostgreSQL full-text search and pgvector semantic search, using a local,
  CPU-feasible PT/EN-capable embedding model.
- Matching in stages: filters, textual retrieval, semantic retrieval,
  structured scoring, and deterministic ranking.
- Unit, integration, API, and end-to-end quality coverage; OpenAPI documentation.
- Docker Compose/local execution and optional free-tier deployment.

## Out of scope

CV parsing; cross-source deduplication/merging or same-opportunity detection;
geographic eligibility classification/filtering; frontend; accounts; automated
applications/ATS submission; CV generation/adaptation; cover letters; mandatory
LLMs; paid or distributed infrastructure; dedicated brokers; indiscriminate
crawling; sophisticated entity resolution or personalization.

The current code is a scaffold: `/health`, candidate profile validation, API
error handling, and an APiBR normalization function exist. Job persistence,
ingestion, indexing, matching, and recommendation endpoints remain planned.
See [MVP tasks](../../specs/feature-001-mvp/tasks.md) for status.
