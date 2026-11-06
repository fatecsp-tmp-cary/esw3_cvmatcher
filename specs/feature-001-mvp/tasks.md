# MVP task status

Status reflects the implementation in this branch.

## Implemented scaffold

- FastAPI app factory, health endpoint, RFC-style errors, and the documented
  `POST /matches` request/response contract. Matching remains unavailable when
  no executor is configured.
- Candidate profile and flat curriculum request schemas with validation.
- Generated OpenAPI documentation for `/health` and `/matches`, including
  required job identity, eligibility, matched skills, and missing requirements
  in populated response contract tests. Mock results include synthetic IDs and
  compatibility details; these are not calculated matching results.
- APiBR payload normalization function (partial mapping only).
- SQLAlchemy/Alembic setup and a tooling-check migration; no real job schema.
- README documents local PostgreSQL and current test setup.

## Pending implementation

- [ ] Resolve the three remaining questions in [acceptance](acceptance.md)
      before dependent implementation.
- [ ] Implement canonical Job and persisted job/source/skill structures.
- [ ] Implement source interface, APiBR polling, run tracking, safe upsert,
      snapshot evidence, source-specific identity, and lifecycle.
- [ ] Implement normalization, requirement extraction, and shared skill taxonomy.
- [ ] Implement PostgreSQL FTS, local embedding generation, pgvector, and
      invalidation/reprocessing.
- [ ] Implement filters, textual/semantic retrieval, scoring, deterministic
      ranking, and regression dataset.
- [ ] Connect the documented matches API to request-scoped candidate
      normalization, retrieval, scoring, and ranking; add production
      authentication.
- [ ] Complete unit/integration/API/e2e coverage, local Compose services,
      deployment configuration, scheduling, and monitoring.

Detailed feature requirements are in [spec](spec.md); completion gates are in
[Definition of Done](../../docs/quality/definition-of-done.md).

## Consolidation verification

- Response consolidation: `pytest tests/api/test_matches_contract.py
  tests/api/test_mock_api.py --no-cov -q`; lint/format and diff checks passed.
- Matching computation and candidate normalization remain pending; contract
  tests use injected executors and deterministic mock data.
- Validation privacy: `pytest tests/api --no-cov -q` passed, including root and
  nested extra-field canaries in error bodies and captured logs for both apps.
  Extra-field error locations retain only the containing object path.
