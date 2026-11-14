# Feature 001: CV-Match MVP

## Behavior

The service receives an already structured CV, validates and normalizes it to a
request-scoped `NormalizedCandidate`, ingests normalized source-specific jobs,
maintains their lifecycle and search indexes, and returns ranked compatible
jobs through `POST /matches`. CV parsing is external. `GET /health` is optional.

The public five-section contract is defined in [acceptance](acceptance.md#resolved-api-contract).
Its lossless transient projection preserves all sections without the UUID or
additional caps. The legacy internal `CandidateProfile` remains a separate API;
it must not reject valid public input through superseded internal bounds. See
[ADR-011](../../docs/architecture/decisions/ADR-011-main-integration-compatibility.md).

The `Job` fields are defined in the [architecture overview](../../docs/architecture/overview.md).
`platform + source_job_id` is unique source identity, not
deduplication. Embedding model/version and ranking algorithm version are
configuration/metadata, not `Job` fields. `source_expires_at` is an explicit
source expiration; absence does not imply expiration. `raw` retention follows
source restrictions. Null job embedding means missing/invalid for the configured
model.

## Ingestion and normalization

The source interface exposes asynchronous `discover`, `fetch_jobs`,
`fetch_job`, and synchronous `normalize` operations. Sources declare
`INCREMENTAL` or `SNAPSHOT`; only a successful complete snapshot may make
absence meaningful. Source adapters should provide stable IDs. MVP source:
APiBR (see [ADR-002](../../docs/architecture/decisions/ADR-002-apibr-mvp-source.md)).
Under [ADR-014](../../docs/architecture/decisions/ADR-014-apibr-listing-presence-is-open-evidence.md),
presence in the APiBR open-vacancy listing is availability evidence: listed jobs
are `ACTIVE` and explicitly closed records are `EXPIRED`, with no default GitHub
requests ([ADR-003](../../docs/architecture/decisions/ADR-003-apibr-availability-and-partial-runs.md)). Reject
malformed records independently and commit valid records as `PARTIAL` with safe
rejected counts; pagination/network failure rolls back job changes. Neither
partial nor unproven scans permit absence-based lifecycle changes.

Normalize raw job data through source parsing, HTML/whitespace/Unicode cleanup,
section detection, skill/keyword extraction, alias normalization, requirement
classification, then canonical Job. Strip HTML while preserving heading,
paragraph, table-cell and list boundaries in descriptions. Normalize Unicode
to NFC and whitespace within each line; other display text collapses whitespace.
Keep `raw` null until retention rights are established. Requirement classes are `REQUIRED`,
`PREFERRED`, and `NICE_TO_HAVE`; detected skills must not automatically be
assumed mandatory. Deterministic dictionaries, aliases, regex, phrase/fuzzy
matching, and section detection complement the selected local GLiNER job-field
extraction strategy. Follow [the extraction plan](../../docs/data/job-field-extraction.md)
for evidence, confidence, contextual requirement classification, model versioning
and failure handling. Pinned offline extraction and bounded job-state processing are implemented; mandatory classification remains disabled pending measured quality approval. PostgreSQL FTS handles DB-level
tokenization, stemming, and ranking.

Use a shared skill taxonomy (`id`, `canonical_name`, `category`,
`parent_skill_id`, `aliases`); candidate-side taxonomy processing is transient.
Examples: Kubernetes (`k8s`, `kube`), PostgreSQL (`Postgres`), JavaScript (`JS`,
`ECMAScript`).

## Lifecycle and indexing

States: `DISCOVERED`, `ACTIVE`, `STALE`, `EXPIRED`. Allowed transitions:
`DISCOVERED→ACTIVE`, `DISCOVERED→EXPIRED`, `ACTIVE→STALE`, `ACTIVE→EXPIRED`,
`STALE→ACTIVE`, `STALE→EXPIRED`. `STALE` means absence from a successful
complete snapshot; incremental absence and failed polls do not change status.
For APiBR, one SNAPSHOT poll that qualifies under ADR-013 marks absent `ACTIVE`
jobs of that source `STALE`
([ADR-015](../../docs/architecture/decisions/ADR-015-qualifying-snapshot-absence-marks-stale.md)).
`STALE→EXPIRED` is approved after three qualifying absence snapshots, including
the first STALE transition; no age trigger is selected (ADR-020). Supporting
counters and expiry implementation remain pending #145. Reliable explicit
`source_expires_at` may expire immediately. Rediscovery reactivates stale jobs.
`EXPIRED` is terminal even if a source later reopens the record.
Retain expired records; physical deletion is out of MVP.

`last_seen_at` tracks successful observation; `last_verified_at` tracks
successful fetch/validation under source semantics. A changed normalized content
hash updates the job, reindexes text, nulls its embedding, and schedules
regeneration. Unchanged content is not updated. Model/version changes
independently invalidate and regenerate embeddings.

Only jobs with successful extraction enter matching retrieval. Active jobs are
ranked first; jobs in any other status only fill the remaining positions after
them, with `eligibility: false`
([ADR-016](../../docs/architecture/decisions/ADR-016-inactive-jobs-complete-ranked-matches.md)).
Extraction readiness is independent of availability; pending/failed extraction
withholds jobs without changing lifecycle state. After three failed extraction
attempts, alert the operator and require explicit retry. See
[extraction policy](../../docs/data/job-field-extraction.md). FTS covers title, company, description,
keywords, skills, normalized requirements, and location. Portuguese any-term FTS
uses A title/skills, B company/keywords/normalized requirements and D
description/location, PostgreSQL JSON text rendering and descending publication
date then platform/source-ID ties under ADR-004/005. All retrieval paths require
successful extraction for current content/configuration. Semantic job representation is title,
normalized skills, requirements, relevant description, location, and mode.
Candidate representation is job titles, occupations, skills, experience,
education, certifications, languages, and preferences. Persist only job
embeddings in pgvector; candidate embeddings stay in memory. Jobs without a
current valid embedding are excluded from semantic retrieval while missing.

## Matching and API

Stages: (1) hard-exclude only sufficiently certain incompatibilities (employment
type, seniority, language, clearly mandatory requirements); (2) textual FTS;
(3) pgvector similarity; (4) structured skill, seniority, experience,
employment-type, and language scores; (5) combine normalized components. No
geographic filtering/scoring. Uncertain extraction should preferably affect
scoring rather than exclusion.

The semantic component follows
[ADR-008](../../docs/architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md):
evaluate each experience title/description and each education entry independently
against each job. Select the three highest semantic experience scores per job,
then aggregate with greater weight for more recent selected experiences. Combine
that result with the highest semantic education score. Use existing education
course/level fields; do not add a public description field. Fewer than three
experiences use all available entries; missing sections never fabricate evidence.
Initial semantic mixing is 80% experience / 20% education; distinct recency
groups use weights 1.5/1.25/1.0 with equal weight for equal recency. Calibration
and reviewed-example validation remain pending; see
[scoring policy](../../docs/match/scoring-policy.md).

Default final score is `0.45 * textual + 0.35 * semantic + 0.20 * structured`;
weights are configurable and component/final scores are `[0,100]`. Score means
compatibility, not employment probability. Public match results include boolean
`eligibility`, `matched_skills[]`, and `missing_requirements[]`; eligibility
means matching eligibility, never geography: it is `false` for a job that is
not currently active. Detail arrays are required and may
be empty. Component scores may remain internal.

The public API contract is documented in [acceptance](acceptance.md) and is
immutable. Extraction, normalization and scoring changes must preserve its field
names, types, requiredness, validation limits, dates/nulls, query, response and
error semantics. Future incompatible changes require a separately versioned,
explicitly approved contract; internal adapters absorb model changes.
`POST /matches` accepts the matching sections of the implemented Sistema
Currículo preview: `curriculo_id`, `formacoes`, `experiencias`, `projetos`,
`competencias`, and `idiomas`. All arrays are required and may be empty. Items
have no IDs; only `curriculo_id` is a UUID. Education and experience use
required `inicio` and nullable `fim` calendar dates. Education has a level and source status vocabulary;
competency descriptions and language/competency levels are text. Project
technologies are a string. Validation follows the source domain as specified
in acceptance. The outdated integration document does not govern the schema.

The request excludes identity/contact, presentation, and document fields.
Submitted curriculum ID and data are request-scoped: do not persist,
log, or return them. The only query parameter is `limit`, defaulting to 10
and bounded from 1 through 100. Production and mock share the same schema.

The response is `MatchesResponse {matches: MatchResult[]}`. Each result contains
`rank`, `job`, `score`, `eligibility`, `matched_skills`,
`missing_requirements`, `embedding_model`, and `algorithm_version`. The nested
job contains `id` (the stable positive integer persisted job ID), `company`, `title`, `description`, `keywords`, `location`,
`work_arrangement`, `seniority_level`, `skills`, `salary`, `currency`,
`job_url`, and `publication_date`. The `skills` of a result are the job's own
skills plus the skills the worker associated with it from explicit requirement
contexts
([ADR-017](../../docs/architecture/decisions/ADR-017-job-field-evidence-order-and-extracted-skills.md)).
The public contract omits `curriculo_id`
and internal component scores. Ranking order is represented by
array order and `rank`. `GET /health` returns `{"status":"ok"}`. FastAPI
publishes the OpenAPI schema and Swagger UI.

Errors use RFC 9457 `application/problem+json`: `type` is `about:blank`, `title`
is the HTTP phrase, `status` is numeric, `detail` is optional; 422 adds one
`errors` item per invalid field (`loc`, `msg`, `type`). 422 invalid field/JSON;
404/405 unknown route/method (405 includes `Allow`); 503 unavailable required
database/model; 500 generic failure. Bodies/logs omit submitted values and
exception messages; logs include exception type and origin only. Request schemas
use fixed fields. Rejected extra-field errors point to the containing object
(including schema field names and list indexes), omitting the submitted key.

## Persistence, processing, operations

Persist `job_sources`, `source_runs`, `jobs`, `skills`, `job_skills`, and
`job_requirements`; no candidate tables. Source state includes `id`, `name`,
`type`, `polling_mode`, `enabled`, `polling_interval`, `last_run_at`,
`last_success_at`, `next_run_at`, and `last_error`. Run records include
`id`, `source_id`, timestamps, status, snapshot completeness, found/created/
updated/unchanged/rejected/lifecycle counts, and errors; capture enough evidence to establish
snapshot safety, duration, polling mode, and parsing/HTTP/indexing/embedding
failures. Scheduler flow: lock source → poll/fetch → validate → normalize →
upsert → lifecycle update → schedule indexing/embedding. Distinguish found,
created, updated, unchanged, and absent-from-complete-snapshot. PostgreSQL locks
prevent overlapping same-source runs/conflicting lifecycle operations.

Worker handles polling, normalization, expiration, indexing, embedding, and
model-change reprocessing. Scheduler may be bundled or separate. Embedding work
is asynchronous and does not block ingestion/API requests. Record matching
duration. Credentials use environment/secrets; production uses HTTPS, restricted
DB access, data minimization, relevant LGPD principles, and an open API with no authentication.
A PostgreSQL-coordinated global rolling limit admits at most 60 HTTP requests
per minute; excess returns privacy-safe 429. See
[ADR-010](../../docs/architecture/decisions/ADR-010-preproduction-and-minute-rate-limit.md).

Local Compose includes PostgreSQL+pgvector, API, worker; local model is cached
in a persistent volume. Deployment stays provider-independent, prefers free
tiers/open-source/GitHub Actions, and verifies persistent PostgreSQL, pgvector,
scheduling, background processing, inference, and actual free-tier limits at
deployment time.

## Docker Compose deployment

Docker Compose is the required packaging and execution path for local use and
single-host deployment. Provide the production API, background worker/scheduler
(bundled or separate under the existing architecture), and PostgreSQL+pgvector.
The standalone mock API is a development aid and does not satisfy this requirement.

Persist PostgreSQL data and cached local models, including selected embedding
and GLiNER artifacts, across container replacement. Supply environment-specific
configuration and credentials outside images and version control. Document model
preparation, schema migration ordering, database readiness and application/model
readiness so requests are not served against an incompatible or unready stack.
Keep background polling/extraction/indexing functional under Compose.

Provide a reproducible operator procedure for build/start, migrations, readiness
checks, update, restart, shutdown without volume loss, backup/restore and recovery
from failed startup or migration. Preserve production HTTPS, the global
60-requests/minute admission limit, restricted database access and candidate-data
privacy requirements. Authentication is intentionally absent under ADR-009.
The same immutable Sistema Currículo integration contract applies to deployed APIs.
Hosting remains provider-independent; verify actual host CPU, memory, storage and
model requirements. A successful mock or database-only startup is not full-stack
deployment verification.

## Extraction correction policy (issue #116)

[ADR-018](../../docs/architecture/decisions/ADR-018-extraction-context-and-approximate-evidence.md)
governs clause-local cue attribution, section fallback, negated-null and hedged
NICE_TO_HAVE evidence, strongest-class consolidation with retained conflict flags,
smallest meaningful exact Unicode spans, dedicated internal entity labels and
bounded score-only typo matching on both job/candidate sides. Detection is separate
from requirement selection; background detections cannot become requirements.
No canonical Job/public API change or new hard exclusion is permitted. Original
reviewed evidence is preserved; policy-updated copies are calibration/regression
material and cannot renew held-out independence.

## Bilingual search interview — issues #147/#159

Authority: [ADR-022](../../docs/architecture/decisions/ADR-022-bilingual-ascii-search-and-fuzzy-fallback.md).

Use a separate lower-case ASCII projection, Portuguese and English stemming, and bounded fuzzy fill-only retrieval under ADR-022. Original Unicode/display/span evidence stays intact. The current Portuguese FTS remains the implemented baseline until the planned change is verified.

## Mandatory coverage interview — issue #120

Authority: [ADR-021](../../docs/architecture/decisions/ADR-021-mandatory-coverage-score-only.md).

Only explicit REQUIRED concepts enter the ADR-021 threshold: all below three, otherwise max(3, ceil(70% of N)). Exact/approved-alias evidence alone satisfies it. All exclusions remain off; this is not a replacement for evaluation gates.

## Deferred external deployment and source expansion

Authority: [ADR-023](../../docs/architecture/decisions/ADR-023-deferred-external-deployment-and-second-source.md).

External hosting/HTTPS deployment and second-source research/selection remain deferred. Local pre-production and APiBR remain the authorized scope.

## Stale expiration interview — issue #145

Authority: [ADR-020](../../docs/architecture/decisions/ADR-020-three-snapshot-stale-expiration.md).

The accepted expiration threshold is three qualifying absence snapshots, including the one that first marks STALE. No age-based threshold is selected. Bad scans do not advance the count; rediscovery resets it. Supporting counters remain outside canonical Job.

## Field-evidence interview — issue #196 / PR #197

Authority: [ADR-019](../../docs/architecture/decisions/ADR-019-title-first-job-evidence-and-displayed-skills.md).

Job field source priority is title > typed labels > named/checked body fields. Resolve title/selected-body values by the approved orders; conflicting labels may fall through to checked body options; specialist/coordinator ties use first occurrence. Add only exact affirmative non-conflicting extracted skills to displayed source skills. Current draft code still implements ADR-017 and requires correction.
