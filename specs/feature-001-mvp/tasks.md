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
