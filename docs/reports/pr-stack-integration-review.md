# PR stack restack audit

The user corrected the earlier consolidation on 2026-11-07. PR #130 is restored
exactly to `d305975`, and the ten PRs form one linear chain above it:
`#130 → #101 → #104 → #105 → #106 → #107 → #108 → #109 → #110 → #111 → #112`.
Each child targets its immediate predecessor. The rejected combined head
`59f2006` is retained only as a local recovery/evidence ref, not on #130.

## Confirmed intentions

- Retain the earlier behavioral decisions and distribute each fix and its
  documentation to the responsible PR, including collection caps in #112.
- Keep the 22 focused issues (#132–#153), preserving valid corrections and
  updating references to the corrected stack. #99 remains open.
- Keep the CI workflow unchanged. Use a temporary draft validation PR from #112
  to main for full checks, then close it without merging.
- Preserve original source commits where compatible; resolve obsolete public
  DTO/endpoint changes onto the existing #130 contract.

## Review evaluations and ownership

| PR | Review evidence and retained disposition |
| --- | --- |
| #101 | Changes requested, later approval: fix heading/table word joining and preserve sections; correct fixture provenance. Canonical migration/identity decision is ADR-007. Real APiBR capture remains #132; do not close #99. |
| #104 | Approved on non-database tests: retain the small deterministic hash helper; database invalidation evidence belongs to the dependent persistence tests. |
| #105 | Approved on non-database tests: move persistence tests to PostgreSQL and preserve source independence; concurrent conflict safety remains #136. |
| #106 | Changes requested: remove hidden unauthenticated requests, isolate rejected records, record PARTIAL counts and test transport rollback without network. ADR-003 governs availability/failure behavior. |
| #107 | Changes requested: document language, accents, HTML, JSON representation, weighting and query semantics. ADR-004/ADR-005 govern the initial search decision. |
| #108 | Approved on non-database tests: retain taxonomy/association/requirement schema and migration coverage; seeding/extraction remain #137/#138. |
| #109 | Changes requested: replace non-immutable index expressions and AND queries with matching weighted any-term expressions. Cast parsed query text to TSQUERY to avoid double stemming. Active-only and deterministic retrieval remain required. |
| #110 | No review recorded: independently preserve unknown-as-no-category semantics and shared domain enum imports; language/employment hard-filter mappings remain #139. |
| #111 | Changes requested: inherit #130's job ID, eligibility, details, callable boundary and RFC errors; add precise response-validation tests instead of restoring the incompatible endpoint. |
| #112 | Changes requested: use current preview names/dates, preserve all sections and levels, accept empty evidence, apply approved caps and test adapter/privacy boundaries. ADR-006 supersedes the old uncapped-array policy. |

Only layers through this branch's PR are implemented here; later dispositions
are the approved plan until their branches are reached. The governing feature
status is [tasks](../../specs/feature-001-mvp/tasks.md).

## Focused backlog

- [#132](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/132): Capture verified APiBR response fixtures and field mappings
- [#133](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/133): Implement the common asynchronous source adapter interface
- [#134](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/134): Verify APiBR access, rate-limit and payload-retention permissions
- [#135](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/135): Add bounded APiBR retries and rate-limit backoff
- [#136](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/136): Make concurrent source-identity upserts safe in PostgreSQL
- [#137](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/137): Seed the shared skill taxonomy and normalize aliases on both sides
- [#138](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/138): Extract and persist classified job requirements from preserved sections
- [#139](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/139): Define language and employment requirement mappings before hard filters
- [#140](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/140): Persist job embedding model-version and dimension metadata
- [#141](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/141): Reprocess job vectors after embedding-model version changes
- [#142](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/142): Prevent overlapping source runs with PostgreSQL coordination
- [#143](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/143): Schedule enabled sources and maintain polling timestamps
- [#144](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/144): Queue and retry background embedding work in PostgreSQL
- [#145](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/145): Expire STALE jobs using approved missing-snapshot and age thresholds
- [#146](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/146): Apply reliable source expiration timestamps in the lifecycle worker
- [#147](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/147): Evaluate English and accent behavior in the Portuguese FTS baseline
- [#148](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/148): Record matching duration without retaining candidate data
- [#149](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/149): Verify PostgreSQL backup and restore recovery
- [#150](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/150): Verify deployment capabilities and free-tier limits
- [#151](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/151): Define and enforce privacy-safe request processing budgets
- [#152](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/152): Define matching behavior for an all-empty valid curriculum
- [#153](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/153): Add optional authenticated availability verification with bounded request budgets

## Verification by layer

- PR #101: 172 unit/API tests passed; repository lint/format passed. PostgreSQL execution is pending the separate validation route.
- PR #104: 175 unit/API tests passed; repository lint/format passed. PostgreSQL execution is pending the separate validation route.
