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

The original branches were rebased separately, with #130 exactly at `d305975`.
Each layer retains its own scope and fixes. Per-layer unit/API checks passed;
linearity, feature boundaries, one migration head and documentation references
were checked across all ten branches. The CI workflow is unchanged.

At source head `11d89e8`,
[CI run 42345643778](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/actions/runs/42345643778)
passed 229 unit/API tests and 31 PostgreSQL/pgvector integration tests, plus
lint/format and branch validation. The approved temporary draft #154 supplies
this cumulative CI route; closing it without merging or deleting #112's head
branch is required after final checks. Source PR bases remain unchanged.

[The restack audit](../../docs/reports/pr-stack-integration-review.md) records
review evaluations, the interview, per-layer checks, issue corrections and
validation evidence. The rejected combined #130 head is historical recovery
material only, not the implementation or verification target.
