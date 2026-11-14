# Architecture decision records

ADRs record architectural decisions, rationale, and consequences. Accepted decisions are
superseded by later ADRs; do not rewrite their rationale or status history.

- [ADR-001: Core privacy, source identity, and matching boundaries](ADR-001-core-boundaries.md)
- [ADR-002: APiBR as the MVP source](ADR-002-apibr-mvp-source.md)
- [ADR-003: APiBR availability evidence and partial ingestion](ADR-003-apibr-availability-and-partial-runs.md)
- [ADR-007: Canonical persistence alignment and source identity](ADR-007-canonical-persistence-alignment.md)

- [ADR-008: GLiNER extraction, fixed integration contract and semantic evidence](ADR-008-extraction-contract-and-semantic-evidence.md)

- [ADR-009: Open API with global admission limit](ADR-009-open-api-global-rate-limit.md)

- [ADR-010: Pre-production scope and corrected rate-limit interval](ADR-010-preproduction-and-minute-rate-limit.md)

- [ADR-004: Portuguese PostgreSQL full-text search](ADR-004-portuguese-full-text-search.md)
- [ADR-005: Weighted any-term Portuguese retrieval](ADR-005-weighted-any-term-fts.md)
- [ADR-006: Curriculum projection and collection bounds](ADR-006-curriculum-projection-and-bounds.md)
  — collection caps superseded by ADR-008's frozen uncapped contract, recorded in ADR-011;
  its lossless projection requirements remain applicable.
- [ADR-011: Main integration compatibility record](ADR-011-main-integration-compatibility.md)
  — records existing authority, preserving ADR-004/005/006 unchanged. ADR-010
  supersedes ADR-009's interval and rollout-availability requirement.

- [ADR-012: Issue completion and reviewed evaluation](ADR-012-issue-completion-and-evaluation-policy.md) — accepted interview decisions for request budgets, conservative mappings, evaluation and local deployment scope.

- [ADR-013: Best-effort APiBR snapshot attestation](ADR-013-best-effort-apibr-snapshot-attestation.md) — accepted conditional source-health/count completeness, without availability or absence-driven expiry.

- [ADR-018: Clause-local extraction and approximate score evidence](ADR-018-extraction-context-and-approximate-evidence.md) — accepted 2026-11-14 interview; score-only, strongest occurrence, typo support and reused-set evaluation limitations.

## Identifier provenance

ADR-014 denotes APiBR availability on the later source stack; ADR-018 denotes
the extraction interview. The former extraction ADR-014 path is a historical
redirect. ADR-015/016 remain the accepted snapshot-absence/inactive-result
decisions. ADR-017 remains the original field-evidence proposal. Frozen reports
and machine policy identifiers keep their original bytes and are not new authority.
New interview records 019–023 are added on their owning branches as listed below.

- [ADR-022: Bilingual ASCII search projection and bounded fuzzy fallback](ADR-022-bilingual-ascii-search-and-fuzzy-fallback.md) — accepted interview policy; implementation status is tracked separately.

- [ADR-021: Exact-evidence mandatory coverage remains score-only](ADR-021-mandatory-coverage-score-only.md) — accepted interview policy; implementation status is tracked separately.
