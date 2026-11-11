# MVP task status

Requirements and completion gates are in [spec](spec.md),
[acceptance](acceptance.md), and the
[Definition of Done](../../docs/quality/definition-of-done.md).

## Implemented

- Shared production/mock preview request and ranked response, OpenAPI, limit, health and privacy-safe RFC 9457 errors.
- Canonical job correction, source identity and four lifecycle states; section-preserving HTML cleanup. Raw remains null.
- Deterministic normalized content hashing.
- Source-specific upsert, content/vector invalidation and stale rediscovery; PostgreSQL persistence tests. Identity advisory locks serialize competing inserts/updates and refresh stale ORM rows; source scheduling and batch deadlock retry remain pending.
- Sequential incomplete APiBR scans, unknown availability without GitHub requests, isolated malformed records, PARTIAL/FAILED run evidence and PostgreSQL regressions.

## Pending components

- [ ] Portuguese weighted any-term FTS field/query/normalization decisions.
- [ ] Skill taxonomy, job-skill and classified requirement persistence; population/extraction remain pending.
- [ ] Immutable weighted FTS indexes, active-only any-term/requirement retrieval and stable ties; no semantic or final score implementation.
- [ ] Domain-enum seniority/mode aliases; missing/unknown values yield no category. Other categories remain text.
- [x] Ranked response validation tests for job identity, eligibility, match details and version metadata.
- [x] Lossless transient adapter preserving every source section/date/level, accepting empty sections and omitting the UUID. It imposes no additional public caps. Production executor wiring remains pending.
- [ ] Collection-cap conflict remains governed by the frozen public contract; do not impose caps implicitly.

## Remaining MVP work

- [ ] Source evidence/interface/retries: #113/#115/#132–#135; optional bounded
      availability verification #153. Real payload capture remains pending.
- [ ] Production concurrency, taxonomy and requirement extraction:
      #116/#136–#139/#142. Preserve source independence and uncertain evidence.
- [ ] Lifecycle policies: #117/#145/#146. Never infer absence from an unproven scan.
- [ ] Model selection, metadata, semantic retrieval and scoring:
      #26/#118–#120/#140/#141/#152; textual normalization/ranking and regression
      fixture #30/#31/#33/#34 and vertical-slice validation #45–#49.
- [ ] API pipeline, open backend integration (no authentication; browser CORS disabled),
      worker and operations:
      #121–#124/#143/#144/#148–#151; language/accent investigation #147.
- [ ] Release coverage #125 and the initial textual slice #9. #99 remains open.
- [ ] Additional-source selection/adapter #127/#128 are separate from the
      at-least-one-source MVP acceptance minimum.

## Approved requirements awaiting implementation (2026-11-11)

- [ ] Implement [GLiNER job-field extraction](../../docs/data/job-field-extraction.md),
      with pinned model/configuration, span/context evidence, taxonomy mapping,
      conservative requirement classification and versioned reprocessing.
- [ ] Define extraction quality/runtime targets and remaining retry/alert details;
      implement the accepted success-only readiness gate and three-attempt/manual-retry
      policy; validate
      reviewed PT/EN fixtures independently of weak source labels.
- [ ] Enforce the immutable Sistema Currículo contract with compatibility regressions
      for schema, accepted payloads, limits, query, response and privacy-safe errors.
- [ ] Resolve the collection-cap conflict recorded in
      [acceptance](acceptance.md#pending-implementation-decisions) before cap work
      or merging a different baseline. Existing public caps must not be inferred.
- [ ] Evaluate every experience title/description and education entry per job;
      select the three highest semantic experience scores, weight recent selected
      experiences more, and combine with the highest semantic education score.
- [x] Implement/test deterministic semantic aggregation of calibrated per-entry
      scores: top-three relevance selection, recency ties, initial 1.5/1.25/1.0
      weighting, best education, 80/20 mix and available-section normalization.
      Inference, calibration, reviewed fixtures and API wiring remain pending.
- [ ] Validate/version the initial 80% experience / 20% education semantic mix
      selected during implementation interview; set calibration and recency weights; cover
      selection versus recency, ties, empty/fewer entries and deterministic ranking.

These decisions are documented in
[ADR-008](../../docs/architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md).
GLiNER inference and production scoring/API wiring remain pending. The
calibrated-score aggregation primitive is implemented; the public schema is unchanged.

## Docker Compose deployment

Current `docker-compose.yml` provides PostgreSQL+pgvector only;
`docker-compose.mock.yml` and `Dockerfile.mock` provide a standalone mock API.
Full production deployment remains pending.

- [ ] Package the production API and worker/scheduler with PostgreSQL+pgvector
      under Compose, retaining the existing architecture and public contract.
- [ ] Configure persistent database/model-cache volumes, external configuration
      and secrets, migration ordering and database/application/model readiness.
- [ ] Document build/start, model preparation, migrations, update/recovery,
      restart, non-destructive shutdown and backup/restore.
- [ ] Verify clean deployment, fixture ingestion through production matching,
      background processing, restart persistence and backup/restore using the
      [deployment acceptance criteria](acceptance.md#docker-compose-deployment-acceptance).

## Open API admission policy

- [x] PostgreSQL-coordinated global rolling 60-requests/minute limit at the
      production HTTP entry point; privacy-safe 429/Retry-After and fail-closed
      503; independent-connection concurrency and expiry regression tests.
- [ ] Verify HTTPS termination and realistic admission/matching load under the
      production Compose deployment. No authentication is required under
      [ADR-009](../../docs/architecture/decisions/ADR-009-open-api-global-rate-limit.md).
