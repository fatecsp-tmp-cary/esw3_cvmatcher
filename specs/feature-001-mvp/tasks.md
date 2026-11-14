# MVP task status

Requirements and completion gates are in [spec](spec.md),
[acceptance](acceptance.md), and the
[Definition of Done](../../docs/quality/definition-of-done.md).

## Implemented

- Shared production/mock preview request and ranked response, OpenAPI, limit, health and privacy-safe RFC 9457 errors.
- Canonical job correction, source identity and four lifecycle states; section-preserving HTML cleanup. Raw remains null.
- Deterministic normalized content hashing.
- Source-specific upsert, content/vector invalidation and stale rediscovery; PostgreSQL persistence tests. Concurrent safety is pending.
- Sequential incomplete APiBR scans, unknown availability without GitHub requests, isolated malformed records, PARTIAL/FAILED run evidence and PostgreSQL regressions.
- Portuguese weighted any-term FTS field/query/normalization decisions.
- Skill taxonomy, job-skill and classified requirement persistence; population/extraction remain pending.
- Immutable weighted FTS indexes, active-only any-term/requirement retrieval and stable ties; no semantic or final score implementation.
- Domain-enum seniority/mode aliases; missing/unknown values yield no category. APiBR uses first-recognized source-label precedence, retaining every keyword. Other categories remain text.
- Ranked response validation tests for job identity, eligibility, match details and version metadata.
- Public collection caps and a transient adapter preserving every source section/date/level, accepting empty sections and omitting the UUID.

## Remaining MVP work

- [ ] Source payload/scan/usage evidence, shared interface and bounded retries;
      optional bounded availability verification. Real payload capture is pending.
- [ ] Production concurrency, taxonomy population and requirement extraction.
      Preserve source independence and uncertain evidence.
- [ ] Lifecycle policies. Never infer absence from an unproven scan.
- [ ] Model selection, metadata, semantic retrieval, scoring, model-change
      reprocessing and empty-evidence behavior; textual normalization/ranking,
      a fixed regression fixture and vertical-slice validation.
- [ ] API pipeline, authentication, worker scheduling, source locking and
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
