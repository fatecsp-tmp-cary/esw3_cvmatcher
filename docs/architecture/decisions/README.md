# Architecture decision records

Accepted policies and implemented behavior are separate. Preserve original ADRs;
new accepted records supersede the relevant rules rather than rewriting history.

| ADR | Record | Status / current scope |
|---|---|---|
| 001 | [Core privacy, source identity, and matching boundaries](ADR-001-core-boundaries.md) | Accepted |
| 002 | [APiBR as the MVP source](ADR-002-apibr-mvp-source.md) | Accepted, subject to the documented completeness clarification |
| 003 | [APiBR availability evidence and partial ingestion](ADR-003-apibr-availability-and-partial-runs.md) | Accepted |
| 004 | [Portuguese PostgreSQL full-text search](ADR-004-portuguese-full-text-search.md) | Accepted |
| 005 | [Weighted any-term Portuguese retrieval](ADR-005-weighted-any-term-fts.md) | Accepted |
| 006 | [Curriculum projection and collection bounds](ADR-006-curriculum-projection-and-bounds.md) | Accepted |
| 007 | [Canonical persistence alignment and source identity](ADR-007-canonical-persistence-alignment.md) | Accepted |
| 008 | [GLiNER extraction, fixed integration contract and semantic evidence](ADR-008-extraction-contract-and-semantic-evidence.md) | Accepted |
| 009 | [Open API with global admission limit](ADR-009-open-api-global-rate-limit.md) | Accepted |
| 010 | [Pre-production scope and corrected rate-limit interval](ADR-010-preproduction-and-minute-rate-limit.md) | Accepted |
| 011 | [Main integration compatibility record](ADR-011-main-integration-compatibility.md) | Recorded reconciliation of existing accepted authority |
| 012 | [Issue completion, request budgets and reviewed evaluation](ADR-012-issue-completion-and-evaluation-policy.md) | Accepted |
| 013 | [Best-effort APiBR health/count snapshot attestation](ADR-013-best-effort-apibr-snapshot-attestation.md) | Accepted |
| 014 | [APiBR listing presence is open-vacancy evidence](ADR-014-apibr-listing-presence-is-open-evidence.md) | Accepted |
| 015 | [Absence from a qualifying APiBR snapshot marks jobs STALE](ADR-015-qualifying-snapshot-absence-marks-stale.md) | Accepted |
| 016 | [Inactive jobs complete the ranked matches after active jobs](ADR-016-inactive-jobs-complete-ranked-matches.md) | Accepted |
| 017 | [Evidence order for APiBR job fields and extracted skills in results](ADR-017-job-field-evidence-order-and-extracted-skills.md) | Original proposal preserved; field/display rules superseded by ADR-019 |
| 018 | [Clause-local extraction and approximate score evidence](ADR-018-extraction-context-and-approximate-evidence.md) | Accepted extraction policy, renumbered from the colliding extraction ADR-014 |
| 019 | [Title-first job fields and trustworthy displayed skills](ADR-019-title-first-job-evidence-and-displayed-skills.md) | Accepted policy; implementation and verification pending |
| 020 | [Three qualifying absence snapshots expire stale jobs](ADR-020-three-snapshot-stale-expiration.md) | Accepted policy; implementation and verification pending |
| 021 | [Exact-evidence mandatory coverage remains score-only](ADR-021-mandatory-coverage-score-only.md) | Accepted policy; implementation and verification pending |
| 022 | [Bilingual ASCII search projection and bounded fuzzy fallback](ADR-022-bilingual-ascii-search-and-fuzzy-fallback.md) | Accepted policy; implementation and verification pending |
| 023 | [External deployment and second-source selection remain deferred](ADR-023-deferred-external-deployment-and-second-source.md) | Accepted deferral; no external deployment or second source authorized |

## Identifier reconciliation

ADR-014 is APiBR listing availability. ADR-018 is clause-local extraction.
The former extraction ADR-014 path is a historical redirect, not a second current
ADR-014. Its accepted text is preserved in ADR-018. Immutable evidence, source
snapshots, original machine policy identifiers and historical commit links retain
their exact bytes; extraction-specific ADR-014 identifiers in those artifacts
refer to ADR-018. ADR-017 remains its original proposal; ADR-019 records the user’s
different accepted field/display policy.

## Implementation authority

Feature specs/acceptance/plan/tasks and supporting documents track the pending
changes for ADR-019 through ADR-022. Historical test reports do not verify these
new policies. ADR-023 keeps external deployment and source expansion deferred.
No hard exclusions, merge or release approval follow from a documentation update.
