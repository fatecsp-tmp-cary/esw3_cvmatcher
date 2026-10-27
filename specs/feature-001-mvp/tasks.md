# MVP task status

Status reflects the implementation in this branch; it does not imply MVP
completion.

## Implemented scaffold

- FastAPI app factory, health endpoint, and RFC-style error handlers.
- Candidate profile schema and validation.
- APiBR payload normalization with required ID/title validation and partial
  source-field mapping.
- Sequential APiBR polling, source-run tracking, safe source-specific upserts,
  deterministic content hashes, and per-issue availability checks. Runs are
  recorded with `snapshot_complete=false`; no absence-based stale transition is
  applied.
- SQLAlchemy models and Alembic migrations for initial `job_sources`, `jobs`,
  and `source_runs` persistence, with a follow-up revision aligning canonical
  job fields and the unique `(platform, source_job_id)` identity constraint.
  Explicit APiBR state and URL signals update lifecycle; snapshot-based
  lifecycle remains pending.
- README documents local PostgreSQL and current test setup.

## Pending implementation

- [ ] Resolve the three remaining questions in [acceptance](acceptance.md) before dependent implementation.
- [x] Persist the shared skill taxonomy and per-job skill/requirement tables.
- [ ] Complete source-run evidence required by the spec, including parsing,
      HTTP, indexing, and embedding failure details.
- [ ] Prove APiBR snapshot completeness before applying absence-based stale
      transitions; add scheduling and operational retry policy.
- [ ] Implement skill normalization, requirement extraction, and taxonomy
      population.
- [x] Define initial PostgreSQL FTS fields and uniform weighting: title, company,
      description, keywords, skills, normalized requirements, and location.
- [x] Implement Portuguese PostgreSQL FTS retrieval and GIN indexes under
      [ADR-004](../../docs/architecture/decisions/ADR-004-portuguese-full-text-search.md).
- [ ] Implement local embedding generation, pgvector, and invalidation/reprocessing.
- [ ] Implement filters, semantic retrieval, scoring, deterministic
      ranking, and regression dataset.
- [ ] Implement agreed matches API, OpenAPI, privacy-safe errors/logging, and
      production authentication.
- [ ] Complete unit/integration/API/e2e coverage, local Compose services,
      deployment configuration, scheduling, and monitoring.

Detailed feature requirements are in [spec](spec.md); completion gates are in
[Definition of Done](../../docs/quality/definition-of-done.md).
