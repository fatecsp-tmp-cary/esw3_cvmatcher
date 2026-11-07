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
- Domain-enum seniority/mode aliases; missing/unknown values yield no category. Other categories remain text.

## Pending components

- [ ] Ranked response validation tests for job identity, eligibility, match details and version metadata.
- [ ] Public collection caps and a transient adapter preserving every source section/date/level, accepting empty sections and omitting the UUID.

## Remaining MVP work

- [ ] Source evidence/interface/retries: #113/#115/#132–#135; optional bounded
      availability verification #153. Real payload capture remains pending.
- [ ] Production concurrency, taxonomy and requirement extraction:
      #116/#136–#139/#142. Preserve source independence and uncertain evidence.
- [ ] Lifecycle policies: #117/#145/#146. Never infer absence from an unproven scan.
- [ ] Model selection, metadata, semantic retrieval and scoring:
      #26/#118–#120/#140/#141/#152; textual normalization/ranking and regression
      fixture #30/#31/#33/#34 and vertical-slice validation #45–#49.
- [ ] API pipeline, authentication, worker and operations:
      #121–#124/#143/#144/#148–#151; language/accent investigation #147.
- [ ] Release coverage #125 and the initial textual slice #9. #99 remains open.
- [ ] Additional-source selection/adapter #127/#128 are separate from the
      at-least-one-source MVP acceptance minimum.
