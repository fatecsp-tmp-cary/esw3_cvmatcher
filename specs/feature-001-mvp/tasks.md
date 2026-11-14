# MVP task status

Requirements remain governed by [spec](spec.md), [acceptance](acceptance.md),
accepted ADRs and the [Definition of Done](../../docs/quality/definition-of-done.md).
Implementation below is distinct from release approval. #99 remains open.

## Implemented and reconciled with main

- Frozen Sistema Currículo request/query/response contract, lossless transient
  normalization, empty sections, OpenAPI and privacy-safe errors.
- Canonical jobs, platform/source identity, normalized content hashes, terminal
  EXPIRED and stale rediscovery; no cross-source deduplication/geographic filtering.
- Conservative APiBR ingestion, common asynchronous adapter, bounded retries and
  partial/failure handling. Unproven scans never establish absence.
- APiBR label metadata maps to canonical seniority, work arrangement and skills
  through exact shared aliases; repository topics, free text and conflicting
  labels are never classified (#180).
- PostgreSQL identity/source scheduling locks, bounded background cycles and
  reliable source-timestamp expiration. Optional poll on worker start and a
  configured daily local polling time, 08:00 America/Sao_Paulo in Compose (#184).
  An idempotent operator command registers the supported source (#188).
- Separate extraction state/evidence, content/config readiness, concurrent claims,
  three-attempt failure and explicit retry. Failed jobs are withheld from matching.
- Pinned offline local GLiNER inference with token-aware full-text coverage,
  validated offsets/deduplication and conservative explicit skill aliases.
  Mandatory classifications remain disabled pending measured quality approval.
- Weighted Portuguese any-term FTS and bound queries reconciled with ADR-004/005
  weights/fields, JSON text rendering and publication-date/identity ties, with
  current extraction readiness on every retrieval path. Both migration histories
  merge at b1e004; b1e005 rebuilds all three matching FTS indexes.
- Main taxonomy persistence and category aliases retained; both projection APIs
  remain compatible without superseded internal caps (ADR-011).
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

The earlier reconciled database suite passed **608 tests** (one opt-in model benchmark
was deselected), and mypy passed all 60 source files. After independent review,
the primary integrated a bounded-score regression and strengthened the dependency
checker; 171 API/worker/ranking tests and 10 checker tests passed. Ruff lint/format
and the reconciled production image build passed. See the
[current validation report](../../docs/reports/2026-11-12-mvp-validation.md).

## Measurements and release work

- [x] Actual cached offline GLiNER/E5 CPU execution demonstrated on synthetic text.
- [x] Complete warm CPU reference: 10 experiences, 5 education entries, 10,000
  ACTIVE jobs, limit=10, one request at a time. Three measured requests:
  reconciled isolated run: 3.417/3.427/3.498 seconds. The earlier historical run
  was 2.157/2.111/2.133 seconds. A run overlapping image imports failed at
  4.111/4.270/9.516 seconds; retain that evidence and serialize heavy checks.
  Homogeneous synthetic corpus and repeated entries;
  this does not guarantee arbitrary-request latency or model quality.
- Synthetic 40 PT/10 EN semantic AUC was 0.989/0.994/1.0 across measured variants;
  accuracy was 72%. Mandatory recall was zero: quality gates fail and mandatory
  exclusions remain disabled. These are agent-reviewed synthetic examples, not
  human-reviewed labels or release calibration.
- [x] Prepare the existing 40 PT/10 EN cases for blind human review, as requested.
  See the [packet and instructions](../../docs/match/human-review/README.md); all
  reviews are pending and no approval flags changed.
- [ ] Independently reviewed PT/EN quality/calibration and sample sufficiency
  approval. At least 95% precision and 80% recall are required before mandatory
  extraction can exclude candidates; unclassified evidence never hard-excludes.
- [x] Conservative language/employment mappings and certainty rules under ADR-012;
  unknown free text remains supporting evidence. All new hard exclusions remain
  disabled pending the independently reviewed quality gates.
- [ ] APiBR terms/retention evidence (#113/#132/#134).
  ADR-013 separately defines and tests best-effort scan completeness. Raw
  retention, hidden availability calls and absence-driven lifecycle changes
  remain disabled.
- [x] APiBR availability under accepted ADR-014 (#181): presence in the
  open-vacancy listing of the source makes a job ACTIVE and advances
  verification. The optional verifier remains #153.
- [x] Absence under accepted ADR-015 (#186): ACTIVE jobs missing from a qualifying
  SNAPSHOT poll become STALE and rediscovery reactivates them. STALE→EXPIRED
  thresholds remain #145; sources default to INCREMENTAL, where absence is ignored.
- [x] Pre-reconciliation production image build and real pinned offline Compose
  smoke: migrations, synthetic ingestion, worker GLiNER/E5, deterministic API,
  database/API replacement durability and dump/restore into an empty project.
  Actual evidence: `/workspace/cvmatcher-smoke-8bd3a93bc1/report.json`,
  `passed: true`, `production_deployed: false` (local evidence). Parent copied
  this evidence to `docs/reports/2026-11-12-compose-smoke.json`; parent owns
  that report and final integrated counts.
- [x] Primary reran integrated database/static/migration/image/Compose acceptance
  after main reconciliation. The real offline model worker, deterministic API,
  database/API replacement and separate-project dump/restore passed; see the
  [reconciled smoke](../../docs/reports/2026-11-12-compose-reconciled.json).
- [x] Final hashed dependency consistency, local static checks and image build
  after integration. GitHub CI execution remains separately observable on the draft PR.
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

## Replacement-PR issue completion

ADR-012 records the user's 2026-11-12 interview decisions. The original #164 and
#94 remain reference-only drafts; the replacement PRs are merge candidates in
dependency order. Budget, mapping, classification and evaluation-policy changes
are implemented and tested against each issue. Original human annotations, calibration fitting and measured outcomes are complete.
Quality acceptance remains failed; policy-updated copies do not renew held-out
independence. See the extraction correction below for the current evidence. Local deployment acceptance is distinct from external #150.

- [x] Resolve the #125 snapshot-coverage clarification through accepted ADR-013;
  implement/regress qualifying and rejected best-effort count attestations.
  Availability and #145 absence/expiration policy remain separate.

- [x] User annotated the original frozen calibration/held-out packets; reviewed
  results and subsequent policy adjudications are preserved in the correction
  evidence below. Independent post-correction acceptance remains pending.

Final completion verification: **658 passed, 1 external benchmark deselected**.
At the final scoring version, the actual CPU reference failed once with a
20.718-second outlier, then passed at 3.514/3.398/3.484 seconds. Retain both
observations; the repeat is not a guarantee of stable latency. The outlier cause
remains unestablished.
See [completion evidence](../../docs/reports/2026-11-12-issue-completion.md) for
static checks, per-step tests, Compose/recovery scope and remaining human gates.

## Issue #116 extraction correction — 2026-11-14

Policy authority: [ADR-018](../../docs/architecture/decisions/ADR-018-extraction-context-and-approximate-evidence.md).

- [x] Interview and record user decisions before dependent implementation.
- [x] Implement clause-local strengths, negated-null/hedged optional evidence,
      strongest-occurrence consolidation with retained conflict flags, selection
      separate from detection, section/background handling and exact span trimming.
- [x] Add dedicated credential/license/language/certification labels and version
      bounded score-only typo support shared by job/candidate matching.
- [x] Test approved semantic equivalence examples; scalar thresholds do not separate
      related pairs from all distinct languages. Automatic merging remains disabled.
- [x] Complete focused PostgreSQL and full relevant test verification; see
      [correction evidence](../../docs/reports/2026-11-14-extraction-correction.md).
- [x] Update calibration/old-held-out copies with case-level policy provenance on
      evaluation PR #178; preserve originals and historical failures.
- [x] Run calibration only; freeze extraction version, calibration and cutoff;
      preserve PT/EN metrics, failed gates and case errors.
- [ ] Obtain a fresh independently reviewed held-out set for future acceptance.
      Reused held-out labels are regression evidence, not renewed independence.
- [ ] Define minimum mandatory-mention support if future exclusions are proposed.
      All new exclusions remain disabled; no release/merge approval is implied.

## Bilingual search interview — issues #147/#159

- [x] Record the user decision in [ADR-022](../../docs/architecture/decisions/ADR-022-bilingual-ascii-search-and-fuzzy-fallback.md).
- [ ] Implement and compare the approved separate projection, bilingual retrieval and fuzzy fallback; verify readiness, symbol distinctions, original offsets, group priority, limits and index/rebuild impact. No current implementation completion is claimed.
- [ ] Verify the owning feature acceptance criteria and document results; policy acceptance alone is not implementation completion.

## Mandatory coverage interview — issue #120

- [x] Record the user decision in [ADR-021](../../docs/architecture/decisions/ADR-021-mandatory-coverage-score-only.md).
- [ ] Implement/version per-job coverage and its boundary/evidence tests without changing eligibility, DTOs, existing blend weights or evaluation sample requirements.
- [ ] Verify the owning feature acceptance criteria and document results; policy acceptance alone is not implementation completion.

## Deferred external deployment and source expansion

- [x] Record the user decision in [ADR-023](../../docs/architecture/decisions/ADR-023-deferred-external-deployment-and-second-source.md).
- [ ] Retain external deployment (#150) and second-source selection/adapter (#127/#128) as deferred tasks; do not mark them implemented or choose a provider/source implicitly.
- [ ] Verify the owning feature acceptance criteria and document results; policy acceptance alone is not implementation completion.

## Stale expiration interview — issue #145

- [x] Record the user decision in [ADR-020](../../docs/architecture/decisions/ADR-020-three-snapshot-stale-expiration.md).
- [ ] Implement #145 three-snapshot expiration with count/reset/transaction/source-isolation/terminal-state boundary tests; retain the existing one-snapshot STALE transition and timestamp expiry.
- [ ] Verify the owning feature acceptance criteria and document results; policy acceptance alone is not implementation completion.
