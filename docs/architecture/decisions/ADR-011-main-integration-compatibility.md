# ADR-011: Main integration compatibility record

- **Status:** Recorded reconciliation of existing accepted authority
- **Date:** 2026-11-12
- **Authority:** Existing user decision in [ADR-008](ADR-008-extraction-contract-and-semantic-evidence.md)
  freezes the uncapped public contract and lossless transient projection;
  [ADR-010](ADR-010-preproduction-and-minute-rate-limit.md) corrects admission
  and pre-production reprocessing. This record introduces no new user decision.
- **Supersession:** ADR-008 supersedes only the collection caps in
  [ADR-006](ADR-006-curriculum-projection-and-bounds.md) and internal bounds that
  reject otherwise valid public input. Original accepted ADR-004/005/006 files
  remain unchanged.

## Context and reconciliation

Canonical main integration brings earlier accepted retrieval, taxonomy and
projection work alongside later contract, extraction and scoring requirements.
Preserve both projection APIs and lossless source sections; remove superseded
internal caps without tightening public validation. UUID and candidate content
remain request-scoped, absent from storage and logs.

[ADR-004](ADR-004-portuguese-full-text-search.md) and
[ADR-005](ADR-005-weighted-any-term-fts.md) remain authoritative: Portuguese
plain-text any-term retrieval; A title/skills, B company/keywords/normalized
requirements, D description/location; PostgreSQL JSON text rendering; descending
publication date followed by platform/source identity ties. Raw FTS rank remains
separate from compatibility. Every retrieval path additionally requires ACTIVE
availability and successful extraction for current content/configuration.
Extraction failure never changes availability. Location never drives geographic
eligibility. The final textual/semantic/structured blend remains 0.45/0.35/0.20.

Retain main's taxonomy persistence and category aliases. Integrate migration
branches without rewriting accepted migration history. Parent integration uses
`b1e004` to merge legacy `8c317a55d4b1` with `b1e003`, preserving original
migrations. `b1e005` rebuilds all three FTS indexes with accepted helper
expressions and restores original expressions on downgrade; the primary verified
all three indexes with the exact PostgreSQL drift regression. Integrated results
are recorded in the validation report. Per-entry semantic scoring,
pinned model policies, terminal EXPIRED, source independence and privacy remain.
Admission stays global PostgreSQL-backed rolling 60 requests/minute, anonymous,
with no browser CORS; model changes may use stop/reprocess/restart.

## Alternatives and consequences

Applying the old caps would reject valid frozen-contract requests; silently
changing weights or fields would discard accepted FTS behavior. Neither follows
the existing authority. Preserve historical ADRs and record precedence here.

Reconciliation and integrated database/image/Compose verification passed locally.
Those checks and the real offline Compose smoke do not close
quality/calibration or source-usage gates. See [task status](../../../specs/feature-001-mvp/tasks.md).
