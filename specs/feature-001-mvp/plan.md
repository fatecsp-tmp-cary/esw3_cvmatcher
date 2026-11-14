# MVP implementation plan

The product implementation sequence remains source evidence → canonical data →
normalization/ingestion/lifecycle → indexes → matching → API wiring → operations.
Best-effort source completeness follows accepted ADR-013; absence-based lifecycle changes
require proof of a complete scan.

1. Apply ADR-013 count/health attestation for explicit SNAPSHOT configurations;
   verify remaining APiBR usage/retention evidence (#134) and keep unsupported scans incomplete
   until proven. Implement the shared interface and bounded retries (#133/#135).
2. Canonical persistence and source identity, hashing, source-specific upsert,
   and conservative partial-safe ingestion. Concurrent upsert
   and source locking remain #136/#142; scheduling remains #143.
3. Shared taxonomy persistence, seed and classified requirements (#137/#138).
   Preserve description sections and unknown extraction semantics.
4. Reconcile index/queries with accepted ADR-004/005 weights, JSON text rendering,
   publication-date/identity ties and current extraction readiness on all paths. Keep raw
   rank distinct from final compatibility scores; evaluate English/accents #147.
5. Retain category aliases, taxonomy persistence and public response validation;
   preserve both projection APIs and remove superseded internal caps under ADR-011.
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
  error log and explicit retry. Retry delays are 30/60 seconds under the extraction policy; pre-production model changes may use
  stop/reprocess/restart without a rolling cutover; external notification services are not required.
- Protect the immutable integration contract throughout. ADR-008 supersedes the
  old collection caps, recorded by [ADR-011](../../docs/architecture/decisions/ADR-011-main-integration-compatibility.md).
  Integrate migration branches without rewriting history and rerun integrated checks.

These additions follow [ADR-008](../../docs/architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md);
implementation status and remaining release verification are tracked in [tasks](tasks.md).

## Docker Compose deployment work

Extend packaging/operations work (#124/#148–#151) to deliver the production Compose
stack, persistent database/model volumes, migrations/readiness, background work
and an operator procedure. Validate clean startup, the fixture-to-matching path,
restart persistence and backup/restore against the
[deployment acceptance criteria](acceptance.md#docker-compose-deployment-acceptance).

The real pinned offline Compose smoke passed before main reconciliation. Retest
the integrated tree; quality/calibration and source usage remain release gates.

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

## Deferred external deployment and source expansion

Follow [ADR-023](../../docs/architecture/decisions/ADR-023-deferred-external-deployment-and-second-source.md). Retain external deployment (#150) and second-source selection/adapter (#127/#128) as deferred tasks; do not mark them implemented or choose a provider/source implicitly.
Record measured verification before marking implementation complete. No release or merge is approved by this documentation.

## Stale expiration interview — issue #145

Follow [ADR-020](../../docs/architecture/decisions/ADR-020-three-snapshot-stale-expiration.md). Implement #145 three-snapshot expiration with count/reset/transaction/source-isolation/terminal-state boundary tests; retain the existing one-snapshot STALE transition and timestamp expiry.
Record measured verification before marking implementation complete. No release or merge is approved by this documentation.

## Field-evidence interview — issue #196 / PR #197

Follow [ADR-019](../../docs/architecture/decisions/ADR-019-title-first-job-evidence-and-displayed-skills.md). Update #196 implementation/tests to ADR-019, retaining dotted-name boundaries, exact aliases, approved ordering/ties, checked body fallback, provenance-filtered skills, public DTO shape and score-only safety.
Record measured verification before marking implementation complete. No release or merge is approved by this documentation.
