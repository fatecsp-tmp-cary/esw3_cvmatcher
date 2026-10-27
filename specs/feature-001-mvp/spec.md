# Feature 001: CV-Match MVP

## Behavior

The service receives an already structured CV, validates and normalizes it to a
request-scoped `CandidateProfile`, ingests normalized source-specific jobs,
maintains their lifecycle and search indexes, and returns ranked compatible
jobs through `POST /matches`. CV parsing is external. `GET /health` is optional.

Candidate profile fields:

```text
skills[], job_titles[], occupations[], experience[], education[],
certifications[], languages[], locations[], seniority, years_experience,
preferences
```

Candidate `seniority` text maps to the existing `SeniorityLevel` values:
`intern`/`internship`/`estágio` → `INTERN`; `junior`/`jr`/`júnior` →
`JUNIOR`; `mid`/`middle`/`mid-level`/`pleno` → `MID`; `senior`/`sr`/`sênior`
→ `SENIOR`; `specialist`/`especialista` → `SPECIALIST`; and
`coordinator`/`coordenador(a)` → `COORDINATOR`. Candidate preference modes map
`remote`/`remoto`/`home office`/`teletrabalho` → `REMOTE`;
`hybrid`/`híbrido` → `HYBRID`; and `on-site`/`onsite`/`presencial` →
`ON_SITE`. Matching is case- and accent-insensitive for these aliases. Missing
or unknown values normalize to no category and must not cause hard exclusion.
Language proficiency and employment type have no canonical job fields or enums
yet; keep them as schema-validated free text. They may contribute descriptive
matching evidence, but cannot drive hard exclusion until a canonical mapping is
defined.

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
Under [ADR-003](../../docs/architecture/decisions/ADR-003-apibr-availability-and-partial-runs.md),
new state-free jobs stay `DISCOVERED`, with no default GitHub requests. Reject
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
matching, and section detection are proposed. PostgreSQL FTS uses Portuguese tokenization/stemming for documents and plain-text
queries. [ADR-005](../../docs/architecture/decisions/ADR-005-weighted-any-term-fts.md)
selects any-term queries and PostgreSQL weights A (1.0) for title/skills,
B (0.4) for company/keywords/requirements, and D (0.1) for description/location.
JSON fields use PostgreSQL text rendering. Index/runtime expressions must match
and use immutable functions. Treat query quotes/operators as data; preserve
already parsed lexemes when forming the OR query. English stemming and accent-
insensitive matching are not guaranteed. Location remains descriptive retrieval
text, never a separate geographic compatibility score or eligibility filter.

Use a shared skill taxonomy (`id`, `canonical_name`, `category`,
`parent_skill_id`, `aliases`); candidate-side taxonomy processing is transient.
Examples: Kubernetes (`k8s`, `kube`), PostgreSQL (`Postgres`), JavaScript (`JS`,
`ECMAScript`).

## Lifecycle and indexing

States: `DISCOVERED`, `ACTIVE`, `STALE`, `EXPIRED`. Allowed transitions:
`DISCOVERED→ACTIVE`, `DISCOVERED→EXPIRED`, `ACTIVE→STALE`, `ACTIVE→EXPIRED`,
`STALE→ACTIVE`, `STALE→EXPIRED`. `STALE` means absence from a successful
complete snapshot; incremental absence and failed polls do not change status.
`STALE→EXPIRED` uses configured consecutive missing snapshots and/or maximum
stale duration; either configured condition may expire a job. Reliable explicit
`source_expires_at` may expire immediately. Rediscovery reactivates stale jobs.
`EXPIRED` is terminal even if a source later reopens the record.
Retain expired records; physical deletion is out of MVP.

`last_seen_at` tracks successful observation; `last_verified_at` tracks
successful fetch/validation under source semantics. A changed normalized content
hash updates the job, reindexes text, nulls its embedding, and schedules
regeneration. Unchanged content is not updated. Model/version changes
independently invalidate and regenerate embeddings.

Only active jobs are in active retrieval. FTS covers title, company, description, keywords,
skills, normalized requirements, and location. Semantic job representation is title,
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

Default final score is `0.45 * textual + 0.35 * semantic + 0.20 * structured`;
weights are configurable and component/final scores are `[0,100]`. Score means
compatibility, not employment probability. Public match results include boolean
`eligibility`, `matched_skills[]`, and `missing_requirements[]`; eligibility
means matching eligibility, never geography. Detail arrays are required and may
be empty. Component scores may remain internal.

The public API contract is documented in [acceptance](acceptance.md).
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
`job_url`, and `publication_date`. The public contract omits `curriculo_id`
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
DB access, data minimization, relevant LGPD principles, and authentication for
public candidate-data endpoints.

Local Compose includes PostgreSQL+pgvector, API, worker; local model is cached
in a persistent volume. Deployment stays provider-independent, prefers free
tiers/open-source/GitHub Actions, and verifies persistent PostgreSQL, pgvector,
scheduling, background processing, inference, and actual free-tier limits at
deployment time.
