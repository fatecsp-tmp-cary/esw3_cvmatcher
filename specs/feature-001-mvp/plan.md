# MVP implementation plan

The product implementation sequence remains source evidence → canonical data →
normalization/ingestion/lifecycle → indexes → matching → API wiring → operations.
Source completeness remains unresolved; absence-based lifecycle changes
require proof of a complete scan.

1. Verify APiBR payload/scan/usage evidence (#113/#132/#134); keep scans incomplete
   until proven. Implement the shared interface and bounded retries (#133/#135).
2. Canonical persistence and source identity, hashing, source-specific upsert,
   and conservative partial-safe ingestion. Concurrent upsert
   and source locking remain #136/#142; scheduling remains #143.
3. Shared taxonomy persistence, seed and classified requirements (#137/#138).
   Preserve description sections and unknown extraction semantics.
4. Define weighted Portuguese FTS, then implement its index and queries. Keep raw
   rank distinct from final compatibility scores; evaluate English/accents #147.
5. Category aliases, public response validation, and bounded
   preview-to-profile adaptation.
6. Complete model/version metadata, vectors, retrieval and scoring (#26/#118–#120),
   model-change reprocessing (#141), and empty-evidence behavior (#152).
7. Wire the production API (#121), authentication/privacy (#122), background work
   (#123/#144/#153), lifecycle policies (#117/#145/#146), packaging/operations
   (#124/#148–#151), and release regressions (#125). Keep #99 open.

Current implementation status is in [tasks](tasks.md); requirements
and unresolved decisions are in [spec](spec.md) and [acceptance](acceptance.md).
