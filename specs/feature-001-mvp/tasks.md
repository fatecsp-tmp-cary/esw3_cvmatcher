# MVP task status

Requirements remain governed by [spec](spec.md), [acceptance](acceptance.md),
accepted ADRs and the [Definition of Done](../../docs/quality/definition-of-done.md).
Implementation below is distinct from release approval. #99 remains open.

## Implemented and reconciled with main

- Shared production/mock preview request and ranked response, OpenAPI, limit, health and privacy-safe RFC 9457 errors.
- Canonical job correction, source identity and four lifecycle states; section-preserving HTML cleanup. Raw remains null.
- Deterministic normalized content hashing.
- Reliable explicit-source timestamp expiration with bounded ingestion-stripe
  coordination, indexed due-time selection and unchanged observation/verification
  timestamps. APiBR supplies no supported source expiry and emits null.
- Source-specific upsert, content/vector invalidation and stale rediscovery; PostgreSQL persistence tests. Concurrent identity writes use bounded, ordered
  advisory-lock stripes; APiBR buffers observations before locking and retains
  atomic scan rollback. Independent-connection regressions cover inserts,
  lifecycle updates, reversed overlapping scans and unexpected write failure.
- Bounded sequential APiBR scans and sync/async source adapters with retry policy;
  unknown availability without GitHub requests, isolated malformed records,
  PARTIAL/FAILED evidence and PostgreSQL regressions. Explicit SNAPSHOT mode uses
  ADR-013 best-effort health/count attestation; all remote calls finish before
  identity locking and persistence rejection invalidates qualification.
- Portuguese weighted any-term FTS field/query/normalization decisions.
- Skill taxonomy, explicit project-alias seed, job-skill and classified requirement
  persistence; local pinned GLiNER, exact-alias supplemental detection and ADR-018
  clause-local score-only projection. Versioned evidence, three-claim retry/lease
  recovery and readiness predicate are implemented. FTS helpers require explicit
  extraction readiness. Request-scoped pipeline wiring is implemented in #174;
  production API composition is implemented in #175. Quality/release approval and exclusions stay disabled.
- Immutable weighted FTS indexes and active-only any-term/requirement retrieval
  with fail-closed extraction readiness, bounded textual components and stable
  ties are implemented. Legacy retrieval retains raw rank. Deterministic final
  compatibility primitives, versioned calibration and semantic aggregation are
  implemented in #173 and integrated into the request-scoped pipeline in #174.
- Domain-enum seniority/mode aliases; missing/unknown values yield no category. APiBR uses first-recognized source-label precedence, retaining every keyword. Other categories remain text.
- Ranked response validation tests for job identity, eligibility, match details and version metadata.
- Uncapped public collections and a transient adapter preserving every source section/date/level, accepting empty sections and omitting the UUID.

- Pinned offline E5 inference, complete token windows, job-only provenance,
  bounded claims/retries, content/model/extraction invalidation and semantic
  retrieval are implemented. Passages include normalized requirements and
  deterministic locations under a versioned representation policy. Production
  API composition is implemented in #175; empirical calibration/release acceptance
  remain pending.

- Production API executor and database/model readiness composition are implemented
  lazily with the existing anonymous/global-quota policy. Known dependency failures
  use 503; unexpected application errors use the privacy-safe 500 path. Production
  boundary/factory regressions are recorded in the
  [PR #175 review](../../docs/reports/2026-11-15-pr175-review.md).

- Bounded production worker cycles and per-source scheduling use PostgreSQL
  coordination across polling commits. Extraction/embedding maintenance preserves
  failed current work until explicit retry. Database-only retry locks/refetches
  the job and rejects missing/EXPIRED IDs without changing prior state. See the
  [PR #176 review](../../docs/reports/2026-11-15-pr176-review.md).

- Independent agent-reviewed synthetic fixtures: 40 Portuguese/10 English;
  exact-span/class metrics, per-language reporting and missing-prediction handling.
- Integrated synthetic background-to-API regressions for readiness, source
  independence, privacy, deterministic ranking and empty evidence.

The earlier reconciled database suite passed **608 tests** (one opt-in model benchmark
was deselected), and mypy passed all 60 source files. After independent review,
the primary integrated a bounded-score regression and strengthened the dependency
checker; 171 API/worker/ranking tests and 10 checker tests passed. Ruff lint/format
and the reconciled production image build passed. See the
[historical validation report](../../docs/reports/2026-11-12-mvp-validation.md).

## Remaining current-head work

- [ ] Source usage/permission evidence and worker integration of the async interface;
      optional bounded availability verification. Real payload capture is pending.
- [ ] Complete operational acceptance beyond bounded source scheduling and
      extraction/embedding wiring. Preserve source independence and uncertain evidence.
- [ ] Lifecycle policies. Never infer absence from an unproven scan.
- [ ] ADR-022 textual normalization/retrieval changes, a fixed
      release regression fixture and vertical-slice acceptance validation.
- [ ] Current-head Compose deployment/recovery acceptance; packaging and recovery
      tooling are implemented in #177;
      language/accent investigation remains a tracked follow-up.
- [ ] Fresh independent quality/retrieval acceptance beyond implemented synthetic
      regression coverage; do not treat the working matching slice as missing.
- [ ] Additional-source selection/adapter, separate from the at-least-one-source
      MVP acceptance minimum.

## Historical measurements and release work

The model, CPU and Compose measurements below predate the current review fixes.
They are preserved historical results, not reruns of this head or acceptance of
its revised extraction, embedding-passage and semantic policy versions.

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
  See the [packet and instructions](../../docs/match/human-review/README.md).
  Templates remain historical; the original human annotations were subsequently
  supplied. Policy-updated copies and reused held-out cases do not establish
  fresh independent acceptance; release approval remains false.
- [ ] Independently reviewed PT/EN quality/calibration and sample sufficiency
  approval. At least 95% precision and 80% recall are required before mandatory
  extraction can exclude candidates; unclassified evidence never hard-excludes.
- [x] Conservative language/employment mappings and certainty rules under ADR-012;
  unknown free text remains supporting evidence. All new hard exclusions remain
  disabled pending the independently reviewed quality gates.
- [ ] APiBR terms/retention and independent availability evidence (#113/#132/#134).
  ADR-013 separately defines and tests best-effort scan completeness. The aggregate
  728-record probe established no availability; raw retention, hidden availability
  calls and absence-driven lifecycle changes remain disabled.
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

Historical completion verification: **658 passed, 1 external benchmark deselected**.
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


## PR #167 incremental verification

See the [review record](../../docs/reports/2026-11-14-pr167-review.md) for
GitHub/Codex findings, bounded-lock and independent-connection regressions,
current-head checks and later-adapter integration requirements.


## PR #168 incremental verification

See the [review record](../../docs/reports/2026-11-14-pr168-review.md) for
category-label regression fixes, network-free identity-locking integration,
review dispositions and current-head verification.


## PR #169 incremental verification

See the [review record](../../docs/reports/2026-11-14-pr169-review.md) for
concurrent sweep/upsert coordination, reliable-field preconditions, index
migration and regression verification. Absence/stale-age policies and scheduler
integration remain separate work.


## PR #170 incremental review verification

See the [review record](../../docs/reports/2026-11-14-pr170-review.md) for actual
GitHub/Codex review dispositions and current-head extraction checks. Existing
correction/evaluation history above retains its original evidence scope.


## PR #171 incremental verification

See the [review record](../../docs/reports/2026-11-14-pr171-review.md) for
GitHub/Codex dispositions, requirement-passage and location regressions, policy
invalidation, telemetry import ordering and independent-connection claim checks.


## PR #172 incremental verification

See the [review record](../../docs/reports/2026-11-14-pr172-review.md) for
GitHub/Codex dispositions, post-merge FTS/index checks and the limited accented
JSON-prefix observations. ADR-022 policy remains accepted but unimplemented.


## PR #173 incremental verification

See the [review record](../../docs/reports/2026-11-14-pr173-review.md) for both
review dispositions, retrieval-count validation, available-section normalization
and current-head checks. ADR-021 mandatory coverage is accepted but remains
unimplemented; no new exclusion, blend weight or release approval is introduced.

## PR #174 incremental verification

Request-scoped pipeline union, current-evidence rechecks and deterministic scoring
are implemented. Fake-encoder PostgreSQL regressions cover empty/competency-only
input, deduplication, stale/inactive provenance, invalid vectors/counts, stable
ordering and privacy/geography invariants. See the
[review record](../../docs/reports/2026-11-14-pr174-review.md) for actual results.

## PR #177 incremental verification

Compose packaging and recovery tooling are implemented. Local host database
instructions select the development overlay for startup/status/shutdown and
custom ports; production keeps the database unexposed. Current-head configuration
and review evidence are recorded in [the review report](../../docs/reports/2026-11-15-pr177-review.md).
Operational/model/quality release acceptance remains separate.


## PR #178 incremental verification

Declared fixture provenance is validated before dataset/quality flags are derived.
Original human labels and policy-adjudicated copies remain preserved; reused
held-out evidence cannot grant independent acceptance. Integrated acceptance tests
retain the #174 boundary regressions and compare contrasting job geography/modes
under identical deterministic role evidence. See the
[review record](../../docs/reports/2026-11-15-pr178-review.md) for current checks.
ADR-020/021/022 implementation remains explicitly deferred to follow-ups.
