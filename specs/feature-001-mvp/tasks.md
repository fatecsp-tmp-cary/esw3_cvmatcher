# MVP task status

Requirements remain governed by [spec](spec.md), [acceptance](acceptance.md),
accepted ADRs and the [Definition of Done](../../docs/quality/definition-of-done.md).
Implementation below is distinct from release approval. #99 remains open.

## Implemented before main reconciliation

- Frozen Sistema Currículo request/query/response contract, lossless transient
  normalization, empty sections, OpenAPI and privacy-safe errors.
- Canonical jobs, platform/source identity, normalized content hashes, terminal
  EXPIRED and stale rediscovery; no cross-source deduplication/geographic filtering.
- Conservative APiBR ingestion, common asynchronous adapter, bounded retries and
  partial/failure handling. Unproven scans never establish absence.
- PostgreSQL identity/source scheduling locks, bounded background cycles and
  reliable source-timestamp expiration.
- Separate extraction state/evidence, content/config readiness, concurrent claims,
  three-attempt failure and explicit retry. Failed jobs are withheld from matching.
- Pinned offline local GLiNER inference with token-aware full-text coverage,
  validated offsets/deduplication and conservative explicit skill aliases.
  Mandatory classifications remain disabled pending measured quality approval.
- Weighted Portuguese any-term FTS and bound queries. Integration must restore
  ADR-004/005 weights/fields, JSON text rendering and publication-date/identity
  ties while retaining current extraction readiness on every retrieval path.
- Main taxonomy persistence and category aliases retained; both projection APIs
  must remain compatible without superseded internal caps (ADR-011).
- Pinned local multilingual E5 encoder with full token windows, normalized vectors,
  separate provenance, bounded job maintenance and exact pgvector retrieval.
- Production matching executor: per-entry experience/education inference,
  top-three relevance before recency, best education, available-section 80/20
  semantic aggregation and final 0.45/0.35/0.20 blend. Scores/configurations are
  versioned; cosine calibration remains explicitly provisional.
- PostgreSQL-coordinated global rolling 60-requests/minute admission, all HTTP
  paths, safe 429/Retry-After:60 and fail-closed 503; no authentication or CORS.
- Independent agent-reviewed synthetic fixtures: 40 Portuguese/10 English;
  exact-span/class metrics, per-language reporting and missing-prediction handling.
- Integrated synthetic background-to-API regressions for readiness, source
  independence, privacy, deterministic ranking and empty evidence.

Before main reconciliation, the suite passed **531 tests** (one opt-in model
benchmark deselected). Mypy passed all 58 source files; Ruff lint/format and
production image build passed. These counts do not verify the reconciled tree. See the
[current validation report](../../docs/reports/2026-11-12-mvp-validation.md).

## Measurements and release work

- [x] Actual cached offline GLiNER/E5 CPU execution demonstrated on synthetic text.
- [x] Complete warm CPU reference: 10 experiences, 5 education entries, 10,000
  ACTIVE jobs, limit=10, one request at a time. Three measured requests:
  2.157/2.111/2.133 seconds. Homogeneous synthetic corpus and repeated entries;
  this does not guarantee arbitrary-request latency or model quality.
- Synthetic 40 PT/10 EN semantic AUC was 0.989/0.994/1.0 across measured variants;
  accuracy was 72%. Mandatory recall was zero: quality gates fail and mandatory
  exclusions remain disabled. These are agent-reviewed synthetic examples, not
  human-reviewed labels or release calibration.
- [ ] Independently reviewed PT/EN quality/calibration and sample sufficiency
  approval. At least 95% precision and 80% recall are required before mandatory
  extraction can exclude candidates; unclassified evidence never hard-excludes.
- [ ] Canonical language/employment requirement mappings and confidence before
  corresponding hard filters. Unknown free text remains supporting evidence.
- [ ] APiBR terms/retention and scan-completeness evidence (#113/#132/#134).
  A one-record live shape probe passed; its state-free record does not prove
  availability or completeness. No raw retention, hidden availability calls or absence-based
  lifecycle changes are enabled to conceal this limitation.
- [x] Pre-reconciliation production image build and real pinned offline Compose
  smoke: migrations, synthetic ingestion, worker GLiNER/E5, deterministic API,
  database/API replacement durability and dump/restore into an empty project.
  Actual evidence: `/workspace/cvmatcher-smoke-8bd3a93bc1/report.json`,
  `passed: true`, `production_deployed: false` (local evidence). Parent copied
  this evidence to `docs/reports/2026-11-12-compose-smoke.json`; parent owns
  that report and final integrated counts.
- [ ] Primary reruns integrated tests, static checks, migration/image and Compose
  acceptance after main reconciliation; prior evidence is not an integrated pass.
- [ ] Final hashed dependency consistency/CI/image gates after integration.
- [ ] External HTTPS termination verification belongs to an actual deployment;
  no production deployment or merge is authorized.

## Scope boundaries

ADR-008 supersedes earlier collection caps and incompatible internal bounds;
[ADR-011](../../docs/architecture/decisions/ADR-011-main-integration-compatibility.md)
records existing authority, preserving original ADR-004/005/006 files unchanged. Additional sources (#127/#128) remain separate from
the one-source MVP minimum. No candidate state, UUID, embeddings or results may
be persisted/logged. Model changes use stop/reprocess/restart under ADR-010.

The development host is the approved Ubuntu exception. Debian provisioning and
remaining native/runtime acceptance gaps are not application release evidence.
