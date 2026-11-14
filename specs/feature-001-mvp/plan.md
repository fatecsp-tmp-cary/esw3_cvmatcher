# MVP implementation plan

The product implementation sequence remains source evidence → canonical data →
normalization/ingestion/lifecycle → indexes → matching → API wiring → operations.
Explicit SNAPSHOT configurations use accepted best-effort ADR-013 attestation;
absence-based lifecycle changes remain separate policy/implementation work.

1. Verify remaining APiBR usage/permission evidence. Shared source adapters,
   bounded retries and explicit best-effort snapshot attestation are implemented.
2. Canonical persistence and source identity, hashing, source-specific upsert,
   and conservative partial-safe ingestion. Concurrent upserts and explicit-source
   expiry sweeps now share bounded ordered stripes; source scheduling is pending.
3. Shared taxonomy persistence, seed and classified requirements are implemented
   with pinned local extraction and ADR-018 clause-local score-only projection.
   Preserve sections and unknown/negated evidence. Keep exclusions disabled;
   production scheduling and independent quality acceptance remain pending.
4. Define weighted Portuguese FTS, then implement its index and queries. Keep raw
   rank distinct from final compatibility scores; evaluate English/accents.
5. Category aliases, public response validation, and bounded
   lossless uncapped curriculum projection.
6. Complete model/version metadata, vectors, retrieval and scoring,
   model-change reprocessing, and empty-evidence behavior.
7. Wire the production matching API and privacy, background work and bounded
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
