# MVP task status

Requirements and completion gates are in [spec](spec.md),
[acceptance](acceptance.md), and the
[Definition of Done](../../docs/quality/definition-of-done.md).

## Implemented

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
  extraction readiness; production pipeline/API wiring remains planned in
  #174–#175. Quality/release approval and exclusions stay disabled.
- Immutable weighted FTS indexes and active-only any-term/requirement retrieval
  with fail-closed extraction readiness, bounded textual components and stable
  ties are implemented. Legacy retrieval retains raw rank; final compatibility
  scoring and production pipeline integration remain planned.
- Domain-enum seniority/mode aliases; missing/unknown values yield no category. APiBR uses first-recognized source-label precedence, retaining every keyword. Other categories remain text.
- Ranked response validation tests for job identity, eligibility, match details and version metadata.
- Uncapped public collections and a transient adapter preserving every source section/date/level, accepting empty sections and omitting the UUID.

- Pinned offline E5 inference, complete token windows, job-only provenance,
  bounded claims/retries, content/model/extraction invalidation and semantic
  retrieval are implemented. Passages include normalized requirements and
  deterministic locations under a versioned representation policy. Production
  pipeline wiring and empirical calibration/release acceptance remain pending.

## Remaining MVP work

- [ ] Source usage/permission evidence and worker integration of the async interface;
      optional bounded availability verification. Real payload capture is pending.
- [ ] Scheduler/source-run concurrency and production extraction scheduling/wiring.
      Preserve source independence and uncertain evidence.
- [ ] Lifecycle policies. Never infer absence from an unproven scan.
- [ ] Production retrieval/scoring integration, empty-evidence behavior and
      textual normalization/ranking;
      a fixed regression fixture and vertical-slice validation.
- [ ] API pipeline, anonymous global admission limiting (ADR-009/010), worker scheduling, source locking and
      operations; language/accent investigation.
- [ ] Release coverage and the initial textual matching slice.
- [ ] Additional-source selection/adapter, separate from the at-least-one-source
      MVP acceptance minimum.

## Verification

Calendar-only request dates, empty HTML titles, malformed source URLs/timestamp
ranges, and source-label precedence have regression coverage. Local tests,
lint/format checks, documentation link targets, and offline migration SQL
generation pass. Combined-stack verification: 262 unit/API tests and 33 PostgreSQL/pgvector
integration tests passed on 2026-11-11. Lint, formatting and local document
link targets passed. See the [contribution evaluation](../../docs/reports/2026-11-11-pr-stack-evaluation.md)
for scope and limitations.

## Open documentation clarifications

- [ ] Resolve the three [PR #157 clarifications](acceptance.md#open-documentation-clarifications-from-pr-157):
      future hard-exclusion scope, unnamed integration document and canonical
      correction/creation terminology. Exclusion implementation depends on a
      decision; this integration does not choose one.

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
