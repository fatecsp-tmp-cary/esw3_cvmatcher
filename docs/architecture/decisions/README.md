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
