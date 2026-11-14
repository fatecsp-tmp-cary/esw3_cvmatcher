# MVP task status

Requirements and completion gates are in [spec](spec.md),
[acceptance](acceptance.md), and the
[Definition of Done](../../docs/quality/definition-of-done.md).

## Implemented

- Shared production/mock preview request and ranked response, OpenAPI, limit, health and privacy-safe RFC 9457 errors.
- Canonical job correction, source identity and four lifecycle states; section-preserving HTML cleanup. Raw remains null.
- Deterministic normalized content hashing.
- Source-specific upsert, content/vector invalidation and stale rediscovery; PostgreSQL persistence tests. Concurrent identity writes use bounded, ordered
  advisory-lock stripes; APiBR buffers observations before locking and retains
  atomic scan rollback. Independent-connection regressions cover inserts,
  lifecycle updates, reversed overlapping scans and unexpected write failure.
- Sequential incomplete APiBR scans, unknown availability without GitHub requests, isolated malformed records, PARTIAL/FAILED run evidence and PostgreSQL regressions.
- Portuguese weighted any-term FTS field/query/normalization decisions.
- Skill taxonomy, job-skill and classified requirement persistence; population/extraction remain pending.
- Immutable weighted FTS indexes, active-only any-term/requirement retrieval and stable ties; no semantic or final score implementation.
- Domain-enum seniority/mode aliases; missing/unknown values yield no category. APiBR uses first-recognized source-label precedence, retaining every keyword. Other categories remain text.
- Ranked response validation tests for job identity, eligibility, match details and version metadata.
- Uncapped public collections and a transient adapter preserving every source section/date/level, accepting empty sections and omitting the UUID.

## Remaining MVP work

- [ ] Source payload/scan/usage evidence, shared interface and bounded retries;
      optional bounded availability verification. Real payload capture is pending.
- [ ] Scheduler/source-run concurrency, taxonomy population and requirement extraction.
      Preserve source independence and uncertain evidence.
- [ ] Lifecycle policies. Never infer absence from an unproven scan.
- [ ] Model selection, metadata, semantic retrieval, scoring, model-change
      reprocessing and empty-evidence behavior; textual normalization/ranking,
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


## PR #167 incremental verification

See the [review record](../../docs/reports/2026-11-14-pr167-review.md) for
GitHub/Codex findings, bounded-lock and independent-connection regressions,
current-head checks and later-adapter integration requirements.
