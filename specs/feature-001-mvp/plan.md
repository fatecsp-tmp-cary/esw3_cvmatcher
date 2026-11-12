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
7. Wire the production API (#121), open access/rate limiting/privacy (#122; ADR-009), background work
   (#123/#144/#153), lifecycle policies (#117/#145/#146), packaging/operations
   (#124/#148–#151), and release regressions (#125). Keep #99 open.

Current implementation status is in [tasks](tasks.md); requirements
and unresolved decisions are in [spec](spec.md) and [acceptance](acceptance.md).

## Approved extraction and scoring additions

- For taxonomy/extraction work, implement the local GLiNER strategy after reviewed
  PT/EN fixtures, pinned configuration and evidence/failure policy are defined.
- The implementation interview selected initial 80/20 experience/education
  mixing and modest 1.5/1.25/1.0 recency weighting. Aggregation regressions are
  implemented. Models are pinned and inference/scoring wired. Evaluate the
  independent Portuguese/English fixtures (80/20 mix) and calibrate per-entry
  similarities before release approval.
  Validate the five-second warm CPU reference workload in
  [scoring policy](../../docs/match/scoring-policy.md).
- Implement the success-only extraction readiness gate for every matching path.
  Three failed attempts require persisted failed-job state, a structured local
  error log and explicit retry. Retry delays still need definition; pre-production model changes may use
  stop/reprocess/restart without a rolling cutover; external notification services are not required.
- Protect the immutable integration contract throughout. Reconcile the existing
  collection-cap task with the frozen contract before dependent changes.

These additions follow [ADR-008](../../docs/architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md);
implementation status and remaining release verification are tracked in [tasks](tasks.md).

## Docker Compose deployment work

Extend packaging/operations work (#124/#148–#151) to deliver the production Compose
stack, persistent database/model volumes, migrations/readiness, background work
and an operator procedure. Validate clean startup, the fixture-to-matching path,
restart persistence and backup/restore against the
[deployment acceptance criteria](acceptance.md#docker-compose-deployment-acceptance).
