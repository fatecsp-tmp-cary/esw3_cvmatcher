# MVP implementation plan

The product implementation sequence remains source evidence → canonical data →
normalization/ingestion/lifecycle → indexes → matching → API wiring → operations.
Source completeness remains unresolved; absence-based lifecycle changes
require proof of a complete scan.

1. Verify APiBR payload/scan/usage evidence; keep scans incomplete
   until proven. Implement the shared interface and bounded retries.
2. Canonical persistence and source identity, hashing, source-specific upsert,
   and conservative partial-safe ingestion. Concurrent upsert
   and source locking remain pending; scheduling is also pending.
3. Shared taxonomy persistence, seed and classified requirements.
   Preserve description sections and unknown extraction semantics.
4. Define weighted Portuguese FTS, then implement its index and queries. Keep raw
   rank distinct from final compatibility scores; evaluate English/accents.
5. Category aliases, public response validation, and bounded
   preview-to-profile adaptation.
6. Complete model/version metadata, vectors, retrieval and scoring,
   model-change reprocessing, and empty-evidence behavior.
7. Wire the production API, authentication/privacy, background work and bounded
   availability verification, lifecycle policies, packaging/operations, and
   release regressions. Complete the initial textual matching slice.

Current implementation status is in [tasks](tasks.md); requirements
and unresolved decisions are in [spec](spec.md) and [acceptance](acceptance.md).

## Issue #116 extraction correction

Follow [ADR-018](../../docs/architecture/decisions/ADR-018-extraction-context-and-approximate-evidence.md):
implement clause-local context and requirement projection, preserve raw detections,
add explicit entity labels/span trimming and shared conservative typo support.
Validate deterministic extraction tests and PostgreSQL publication before full
relevant tests; evaluate policy-updated calibration labels only and freeze artifacts.
Preserve old held-out labels/results and designate updated copies regression-only.
Document numerical failures, new blind-review dependency and disabled exclusions.
Implementation belongs to PR #170; downstream evaluation packets/evaluator wiring
belong to PR #178. Verify combined behavior without merging either PR.

## Bilingual search interview — issues #147/#159

Follow [ADR-022](../../docs/architecture/decisions/ADR-022-bilingual-ascii-search-and-fuzzy-fallback.md). Implement and compare the approved separate projection, bilingual retrieval and fuzzy fallback; verify readiness, symbol distinctions, original offsets, group priority, limits and index/rebuild impact. No current implementation completion is claimed.
Record measured verification before marking implementation complete. No release or merge is approved by this documentation.

## Mandatory coverage interview — issue #120

Follow [ADR-021](../../docs/architecture/decisions/ADR-021-mandatory-coverage-score-only.md). Implement/version per-job coverage and its boundary/evidence tests without changing eligibility, DTOs, existing blend weights or evaluation sample requirements.
Record measured verification before marking implementation complete. No release or merge is approved by this documentation.
