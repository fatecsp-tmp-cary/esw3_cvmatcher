# PR stack evaluation — 2026-11-11

## Scope and method

Reviewed the incremental contributions of #156, #104–#112 and #157 against
`main` at `885cdb3`, the product scope, architectural invariants, feature
acceptance criteria and Definition of Done. This report is historical evidence;
current requirements and status remain in `specs/feature-001-mvp/`.

| PR | Contribution retained | Assessment and limits |
| --- | --- | --- |
| #156 | Corrective canonical migration, source identity, lifecycle enum, section-preserving normalization | Preserves the original migration and existing rows; downgrade maps new states explicitly. EXPIRED stays terminal. Raw retention remains disabled. |
| #104 | Deterministic normalized content hashing | Stable JSON encoding and explicit descriptive field set; lifecycle/observation changes do not invalidate vectors. Model-version invalidation remains separate work. |
| #105 | Source-specific upsert | Preserves identity and first observation, updates changed fields and clears stale embeddings; concurrent insert protection is still pending. |
| #106 | Sequential APiBR ingestion and source-run evidence | Per-record savepoints isolate malformed data; failed polls roll back changes. Scans never prove completeness or mark absent jobs stale. No implicit GitHub verification calls. |
| #107 | Portuguese FTS decisions | Defines field weights and any-term retrieval, separating raw rank from public compatibility scores. |
| #108 | Skill taxonomy and classified requirement tables | Adds persistence and migration only; seed/population and extraction remain pending. |
| #109 | Weighted active-only PostgreSQL retrieval and GIN indexes | Query/index expressions agree; requirements contribute to retrieval, parsed lexemes are not stemmed twice, and ties are deterministic. No semantic matching or final scoring. |
| #110 | Shared seniority/work-mode aliases | Reuses domain enums, preserves unknowns and all source labels; first recognized label wins. Language/employment canonical mappings remain pending. |
| #111 | Ranked-response regression coverage | Incremental contribution is tests: identity, eligibility, details and metadata validate the response already inherited from main. No new ranking computation. |
| #112 | Transient curriculum adapter and collection caps | Preserves sections, dates and levels, accepts empty profiles, omits the curriculum UUID. Caps are recorded in accepted ADR-006. Production executor wiring remains pending. |
| #157 | ADR attribution and optional health-contract clarification | Documentation corrections agree with ADR-005 and the implemented health response. Existing branch-name check fails because its branch uses `fix/`; code checks passed on its original head. |

## Integration decisions

Retain the stack's current governing documents when reconciling main's older
scaffold/task descriptions. Main's API implementation merges without source
conflicts. Preserve every original contribution commit through merge commits.
The stack can be incorporated through #156 after its head contains the combined
reviewed result; this avoids squash/rebase duplication of dependent histories.
Draft #94 is outside this stack and is not included.

No new architecture or scope decision is made by this integration. The existing
accepted ADRs govern the contributed behavior. Questions raised in #157 about
future exclusions and document wording are recorded in acceptance/tasks without
silently choosing new requirements.

## Verification

- Unit/API: 262 passed (33 integration tests deselected).
- PostgreSQL/pgvector integration: 33 passed (262 unit/API tests deselected),
  using a dedicated PostgreSQL 17 container and a disposable `_test` database.
- Ruff lint and formatting passed; all relative document link targets exist;
  `git diff --check` passed.
- Checks ran with Python 3.12 in a fresh temporary virtual environment using
  the declared development tools. Existing checkout virtual environments had
  unavailable Python interpreters. API tests required execution outside the
  restricted sandbox.
- No additional implementation defect requiring a code change was established
  in this review. Remaining feature limitations are listed above and in tasks.
  Live APiBR capture, model selection and complete MVP release validation were
  not performed.
