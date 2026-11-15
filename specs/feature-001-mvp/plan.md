# MVP implementation plan

The product implementation sequence remains source evidence → canonical data →
normalization/ingestion/lifecycle → indexes → matching → API wiring → operations.
Explicit SNAPSHOT configurations use accepted best-effort ADR-013 attestation;
absence-based lifecycle changes remain separate policy/implementation work.

1. Verify remaining APiBR usage/permission evidence. Shared source adapters,
   bounded retries and explicit best-effort snapshot attestation are implemented.
2. Canonical persistence and source identity, hashing, source-specific upsert,
   and conservative partial-safe ingestion. Concurrent upserts and explicit-source
   expiry sweeps share bounded ordered stripes. Bounded source scheduling with
   independent-connection per-source locks is implemented in #176.
3. Shared taxonomy persistence, seed and classified requirements are implemented
   with pinned local extraction and ADR-018 clause-local score-only projection.
   Preserve sections and unknown/negated evidence. Keep exclusions disabled;
   production scheduling is implemented in #176; independent quality acceptance
   remains pending.
4. Weighted Portuguese FTS indexes and shared query expressions are implemented,
   with explicit extraction readiness on both job and requirement paths. Keep raw
   rank distinct from bounded textual/final compatibility scores. Production
   API composition is implemented in #175; ADR-022 bilingual/ASCII/fuzzy remains
   a tracked follow-up.
5. Category aliases, public response validation, and bounded
   lossless uncapped curriculum projection.
6. Pinned local embeddings, job-only model/version metadata, versioned passage
   representation, semantic retrieval and model/extraction-change invalidation are
   implemented. Deterministic semantic aggregation and final blend primitives are
   implemented in #173, including count validation and available-section numeric
   bounds. Request-scoped combined retrieval/scoring, empty-input handling and
   final readiness/evidence rechecks are implemented in #174. API composition
   is implemented in #175; validate calibration independently before release approval.
7. Production matching API and privacy-safe readiness/error composition are
   implemented in #175. Bounded background processing and database-only explicit
   retry are implemented in #176. Complete bounded availability verification,
   lifecycle policies and release regressions. Compose packaging/recovery tooling
   is implemented in #177; current-head operational acceptance remains separate. Complete the initial textual matching slice.

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
