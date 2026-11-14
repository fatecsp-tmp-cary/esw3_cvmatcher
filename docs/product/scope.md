# Product scope

## In scope

- Structured CV validation and normalization. Bounded spelling tolerance supports
  scores under [ADR-018](../architecture/decisions/ADR-018-extraction-context-and-approximate-evidence.md);
  approximate matches do not establish canonical equivalence or exclusions.
- Modular multi-source job ingestion, with at least one source for MVP.
- Job normalization, source-specific identity, content-change detection,
  lifecycle management, and expiration.
- PostgreSQL Portuguese full-text search with weighted any-term retrieval
  ([ADR-005](../architecture/decisions/ADR-005-weighted-any-term-fts.md)) and
  pgvector semantic search, using a local,
  CPU-feasible PT/EN-capable embedding model.
- Matching in stages: filters, textual retrieval, semantic retrieval,
  structured scoring, and deterministic ranking.
- Unit, integration, API, and end-to-end quality coverage; OpenAPI documentation.
- Docker Compose for local execution and single-host deployment; optional
  free-tier hosting when its resource and persistence limits support the stack.

## Out of scope

CV parsing; cross-source deduplication/merging or same-opportunity detection;
geographic eligibility classification/filtering; frontend; accounts; automated
applications/ATS submission; CV generation/adaptation; cover letters; mandatory
LLMs; paid or distributed infrastructure; dedicated brokers; indiscriminate
crawling; sophisticated entity resolution or personalization.

Implementation status and remaining work are tracked in
[MVP tasks](../../specs/feature-001-mvp/tasks.md).

External deployment and a second source remain deferred under
[ADR-023](../architecture/decisions/ADR-023-deferred-external-deployment-and-second-source.md).
Their optional future inclusion is not current implementation authorization.
