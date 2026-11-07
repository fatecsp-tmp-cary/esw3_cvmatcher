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
