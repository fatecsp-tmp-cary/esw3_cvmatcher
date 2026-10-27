# MVP task status

Status reflects the implementation in this branch; it does not imply MVP
completion.

## Implemented scaffold

- FastAPI app factory, health endpoint, and RFC-style error handlers.
- Internal candidate profile schema and validation (not yet the Sistema
  Currículo API request schema).
- Pydantic schema for the complete Sistema Currículo request object and a
  transient profile adapter preserving matching-relevant sections.
- `POST /matches` validates that payload, adapts it before invoking the match
  executor, and accepts the documented `limit` and `offset` query parameters.
- Internal request-scoped candidate category normalization maps available
  seniority and work-arrangement values to canonical enums; the Sistema
  Currículo adapter still needs to map its scalar modality preference.
- APiBR payload normalization with required ID/title validation and partial
  source-field mapping.
- SQLAlchemy models and Alembic migrations for initial `job_sources`, `jobs`,
  and `source_runs` persistence, with a follow-up revision aligning canonical
  job fields and the unique `(platform, source_job_id)` identity constraint.
  Lifecycle operations and complete run evidence remain pending.
- README documents local PostgreSQL and current test setup.

## Pending implementation

- [ ] Resolve the remaining questions in [acceptance](acceptance.md) before
      dependent implementation.
- [ ] Complete persisted job/source/run structures, including skills and
      requirements tables and all run evidence required by the spec.
- [ ] Implement source interface, APiBR polling, run tracking, safe upsert,
      snapshot evidence, source-specific identity, and lifecycle.
- [ ] Implement normalization, requirement extraction, and shared skill taxonomy.
- [ ] Implement PostgreSQL FTS, local embedding generation, pgvector, and
      invalidation/reprocessing.
- [ ] Implement filters, textual/semantic retrieval, scoring, deterministic
      ranking, and regression dataset.
- [ ] Implement agreed matches API, OpenAPI, privacy-safe errors/logging, and
      production authentication.
- [ ] Complete unit/integration/API/e2e coverage, local Compose services,
      deployment configuration, scheduling, and monitoring.

Detailed feature requirements are in [spec](spec.md); completion gates are in
[Definition of Done](../../docs/quality/definition-of-done.md).
