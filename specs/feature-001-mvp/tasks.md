# MVP task status

This branch includes the linear stack through PR #112. PR #130 is the
unchanged foundation at `d305975`; later PRs in the stack are not implemented
on this branch. Requirements and completion gates are in [spec](spec.md),
[acceptance](acceptance.md), and the
[Definition of Done](../../docs/quality/definition-of-done.md).

## Implemented on this branch

- #130: Shared production/mock preview request and ranked response, OpenAPI, limit, health and privacy-safe RFC 9457 errors.
- #101: Canonical job correction, source identity and four lifecycle states; section-preserving HTML cleanup. Raw remains null.
- #104: Deterministic normalized content hashing.
- #105: Source-specific upsert, content/vector invalidation and stale rediscovery; PostgreSQL persistence tests. Concurrent safety is pending.
- #106: Sequential incomplete APiBR scans, unknown availability without GitHub requests, isolated malformed records, PARTIAL/FAILED run evidence and PostgreSQL regressions.
- #107: Portuguese weighted any-term FTS field/query/normalization decisions. Runtime/index implementation belongs to #109.
- #108: Skill taxonomy, job-skill and classified requirement persistence; population/extraction remain pending.
- #109: Immutable weighted FTS indexes, active-only any-term/requirement retrieval and stable ties; no semantic or final score implementation.
- #110: Domain-enum seniority/mode aliases; missing/unknown values yield no category. Other categories remain text.
- #111: Ranked response validation tests on the inherited #130 contract; no incompatible endpoint, offset or DTO is reintroduced.
- #112: Public collection caps and a transient adapter preserving every source section/date/level, accepting empty sections and omitting the UUID.

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

## Restack verification

The original branches were rebased separately; each layer keeps only its own
changes and review fixes. Tests and documentation links are checked per layer.
The CI workflow remains unchanged by the user's decision. Full PostgreSQL CI
will run through an approved temporary draft validation PR from #112 to main,
then that PR will be closed without merging. The source stack bases remain
unchanged by that validation route.

Current layer validation results are recorded in the restack audit. The previous
combined #130 CI result is historical evidence, not verification of these new
branch heads.
