# MVP implementation plan

The product implementation sequence remains source evidence → canonical data →
normalization/ingestion/lifecycle → indexes → matching → API wiring → operations.
The user separately selected this delivery order to review small dependent PRs:
`#130 → #101 → #104 → #105 → #106 → #107 → #108 → #109 → #110 → #111 → #112`.
Source completeness remains unresolved; this delivery order never authorizes
absence-based lifecycle changes. Each PR targets its immediate predecessor,
and #130 itself remains at its original `d305975` head.

1. Verify APiBR payload/scan/usage evidence (#113/#132/#134); keep scans incomplete
   until proven. Implement the shared interface and bounded retries (#133/#135).
2. Canonical persistence and source identity (#101), hashing (#104), upsert
   (#105), and conservative partial-safe ingestion (#106). Concurrent upsert
   and source locking remain #136/#142; scheduling remains #143.
3. Shared taxonomy seed and classified requirements (#137/#138); persistence
   is #108. Preserve description sections and unknown extraction semantics.
4. Define weighted Portuguese FTS (#107), then index/query it (#109). Keep raw
   rank distinct from final compatibility scores; evaluate English/accents #147.
5. Category aliases (#110), response validation on the #130 contract (#111),
   and bounded preview-to-profile adaptation (#112). Never restore obsolete DTOs.
6. Complete model/version metadata, vectors, retrieval and scoring (#26/#118–#120),
   model-change reprocessing (#141), and empty-evidence behavior (#152).
7. Wire the production API (#121), authentication/privacy (#122), background work
   (#123/#144/#153), lifecycle policies (#117/#145/#146), packaging/operations
   (#124/#148–#151), and release regressions (#125). Keep #99 open.

Current implementation and verification are in [tasks](tasks.md); requirements
and unresolved decisions are in [spec](spec.md) and [acceptance](acceptance.md).
