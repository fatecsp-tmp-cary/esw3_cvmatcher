# MVP task status

Status reflects the repository inspected during this documentation migration.

## Implemented scaffold

- FastAPI app factory, health endpoint, and RFC-style error handlers.
- Candidate profile schema and validation.
- APiBR payload normalization function (partial mapping only).
- SQLAlchemy/Alembic setup and a tooling-check migration; no real job schema.
- README documents local PostgreSQL and current test setup.

## Pending implementation

- [ ] Resolve the three remaining questions in [acceptance](acceptance.md) before dependent implementation.
- [ ] Implement canonical Job and persisted job/source/skill structures.
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
