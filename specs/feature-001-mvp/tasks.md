# MVP task status

Status reflects the implementation in this branch.

## Implemented scaffold

- FastAPI app factory, health endpoint, RFC-style errors, and the documented
  `POST /matches` request/response contract. Matching remains unavailable when
  no executor is configured.
- Candidate profile and flat curriculum request schemas with validation.
- Production and mock APIs share curriculum and match response schemas;
  canonical job enums are shared without importing persistence into API schemas.
- Generated OpenAPI documentation for `/health` and `/matches`, including
  required job identity, eligibility, matched skills, and missing requirements
  in populated response contract tests. Mock results include synthetic IDs and
  compatibility details; these are not calculated matching results.
- APiBR payload normalization function (partial mapping only).
- SQLAlchemy/Alembic setup, a tooling-check migration, and initial job, source,
  and source-run models/migration. Canonical schema alignment remains pending.
- README documents local PostgreSQL and current test setup.

## Pending implementation

- [ ] Resolve the remaining questions in [acceptance](acceptance.md)
      before dependent implementation.
- [ ] Resolve curriculum source-model mapping (acceptance clarification 5):
      professional/academic periods, education level/status, competency
      description/category, free-text proficiency, project technology format,
      and text bounds. Preserve the agreed API until a mapping or contract
      extension is explicitly decided.
- [ ] Align existing job/source structures with the canonical Job and lifecycle
      requirements; implement persisted skill structures. Track the existing
      field mismatch as unresolved clarification 4 in [acceptance](acceptance.md).
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
- Schema consolidation: unit/API tests and lint/format checks passed. OpenAPI
  component parity and a mock startup with database imports blocked are covered.
- Input bounds: unit/API tests passed, including at-limit and over-limit cases
  for all curriculum arrays and project technology tags in both applications.
  Collection limits follow existing candidate-profile limits where applicable;
  projects allow 50 entries, with up to 100 tags of 1–200 characters each.
- Consolidated validation: 113 unit/API tests passed; source/test lint and format
  checks, documentation links, and `git diff --check` passed. Database integration
  tests were not run for these contract and validation changes.
- Curriculum inspection: compared source domain, CRUD DTOs, preview serializer,
  and integration document at `sistema-curriculo` commit `66af300`. Six synthetic
  requests confirmed 422 rejection of CRUD/preview experience dates, source
  education fields/status, competency field names, string project technologies,
  and a free-text language level outside the API enum. Recorded discrepancies
  without changing runtime schemas or executing the source application's code.
