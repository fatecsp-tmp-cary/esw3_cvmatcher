# CV-Match — Implementation Plan

## Objective

REST API that matches/ranks jobs against a **structured CV JSON**. CV parsing is out of scope — input is already structured.

MVP is open-source, free/local-first, with no paid LLM, embedding API, or required paid infrastructure. Initial sources prioritize **Brazilian opportunities**; this is a source-selection constraint, **not geographic eligibility filtering**.

## In Scope

* Structured CV ingestion and normalization
* Modular multi-source job ingestion (≥1 source for MVP)
* Job normalization and source-specific identity
* `content_hash` change detection
* Lifecycle management and expiration
* PostgreSQL FTS + pgvector semantic search
* Local PT/EN-capable, CPU-feasible embedding model
* Matching: filters → textual → semantic → structured scoring → ranking
* Unit/integration/API/e2e tests
* OpenAPI documentation
* Docker Compose/local execution and optional free-tier deployment

## Explicitly Out of Scope

Job deduplication/cross-source merging, geographic eligibility classification/filtering, frontend, user accounts, automated applications/ATS submission, CV generation/adaptation, cover letters, mandatory LLM, paid/distributed infrastructure, Redis/Kafka/RabbitMQ or other dedicated brokers, indiscriminate crawling, sophisticated entity resolution/personalization.

## Architectural Principles

* Separate ingestion, normalization, indexing, matching/ranking, and API.
* Matching is independent from ingestion.
* Prioritize public APIs/structured sources; scraping is an optional fallback.
* Isolate each source behind a common interface; never couple the domain model to source formats.
* Keep textual search and semantic similarity separate.
* PostgreSQL is the **only application-state store**, including scheduler state and worker locking.
* Candidate profile, embedding, and match results are **request-scoped only**: never persist or log them, including request bodies, exceptions, tracing, or telemetry.
* Ranking must be deterministic given identical normalized inputs, job data, model/version, configuration, and algorithm version.
* Respect source terms, rate limits, robots/access restrictions, and storage restrictions.
* `Job` has exactly the fields defined below; additional persisted data belongs in separate structures.
* Lifecycle status describes availability and is independent of other job properties.
* Expired jobs remain as historical records but are excluded from active retrieval.
* Every source-specific job is independent; **no cross-source deduplication, merging, or same-opportunity detection**.
* Embeddings regenerate independently after job-content changes or embedding-model/version changes.
* Location/mode may be stored, normalized, indexed, and included in matching representations, but are **never used for geographic eligibility classification/filtering**.

## Technology

Python, FastAPI, Pydantic, SQLAlchemy, PostgreSQL + pgvector, local embedding model, async HTTP client, lightweight scheduler/worker, Docker Compose, pytest.

No dedicated queue/broker is required.

## Project Structure

```text
esw3_cvmatcher/
├── docs/
│   └── reports/
│
├── src/
│   ├── api/
│   │
│   ├── indexing/          # text, vector, embeddings
│   │   ├── text/
│   │   ├── vector/
│   │   └── embeddings/
│   │
│   ├── ingestion/         # base, sources, scheduler, worker
│   │   ├── base/
│   │   ├── sources/
│   │   ├── scheduler/
│   │   └── worker/
│   │
│   ├── schemas/           # candidate, job, matching
│   │   ├── candidate/
│   │   ├── job/
│   │   └── matching/
│   │
│   ├── matching/          # filters, textual, semantic, ranking
│   │   ├── filters/
│   │   ├── textual/
│   │   ├── semantic/
│   │   └── ranking/
│   │
│   ├── persistence/       # persisted DB data only
│   │   ├── jobs/
│   │   ├── sources/
│   │   └── skills/
│   │
│   └── normalization/     # candidates, jobs, skills, locations
│       ├── candidates/
│       ├── jobs/
│       ├── skills/
│       └── locations/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docker/
├── docker-compose.yml
├── migrations/
├── scripts/
├── README.md
└── pyproject.toml
```

`schemas/` contains request/response representations. `persistence/` contains persisted data models. Candidate data has no persistence model.

## Canonical Job Entity

Exactly:

```text
id, source, source_job_id, company, title, description, location, mode,
salary, currency, employment_type, requirements, published_at,
source_expires_at, first_seen_at, last_seen_at, last_verified_at,
status, canonical_url, raw, embedding, content_hash
```

`source + source_job_id` is uniquely constrained and represents **source identity, not deduplication**.

* `source_expires_at` = explicit source-provided expiration; absence is not expiration.
* `raw` = retained source payload, subject to source terms/storage constraints.
* `embedding = NULL` = embedding missing/invalid for the currently configured model.
* Embedding model/version and ranking algorithm version are configuration/metadata, not `Job` fields.

## CandidateProfile

Request-scoped and never persisted:

```text
skills[], job_titles[], occupations[], experience[], education[],
certifications[], languages[], locations[], seniority,
years_experience, preferences
```

The external parser supplies the structured JSON. CV-Match validates it and converts it to its internal representation.

The profile must support both textual and semantic matching. Candidate locations remain data but are not used for geographic eligibility.

## Skill Taxonomy

Canonical taxonomy shared by candidates and jobs:

```text
skills
├── id
├── canonical_name
├── category
├── parent_skill_id
└── aliases
```

Examples: `Kubernetes ← {k8s, kube}`, `PostgreSQL ← {Postgres}`, `JavaScript ← {JS, ECMAScript}`.

Candidate-side taxonomy processing remains transient.

## Job Ingestion

Common interface:

```python
class JobSource:
    async def discover(self): ...
    async def fetch_jobs(self, discovered_jobs): ...
    async def fetch_job(self, source_job_id): ...
    def normalize(self, raw_job): ...
```

Sources declare:

* `INCREMENTAL`: returns new/changed jobs; absence means nothing about expiration.
* `SNAPSHOT`: successful run represents the complete covered set; only a **successful complete snapshot** can use absence to mark jobs `STALE`.

Possible adapters:

```text
PublicAPI
ATS: Greenhouse / Lever / Ashby
WebSource: optional fallback
```

Sources should provide stable source-specific IDs whenever available. MVP implements at least one public/structured source.

## Change Detection

```text
normalized Job → content_hash → compare stored hash
```

If unchanged: no content update.

If changed:

```text
update Job → re-index text → embedding = NULL → background regeneration
```

Rediscovery updates the existing `source + source_job_id` record.

* `last_seen_at` = successful observation.
* `last_verified_at` = successful fetch/validation according to source semantics.
* Embedding-model changes invalidate embeddings independently of `content_hash`.

No cross-source identity resolution.

## Job Normalization

```text
Raw Job
→ source parsing
→ HTML/whitespace/Unicode normalization
→ section detection
→ skill/keyword extraction
→ alias normalization
→ requirement classification
→ Canonical Job
```

Requirement classes:

```text
REQUIRED
PREFERRED
NICE_TO_HAVE
```

Detect sections such as Required/Must Have/Requirements and Preferred/Nice to Have/Bonus/Plus.

Use deterministic techniques: dictionaries, aliases, regex, phrase matching, fuzzy matching, section detection.

**Do not assume every detected skill is mandatory.**

PostgreSQL FTS handles DB-level tokenization, stemming, and ranking.

## Job Lifecycle

States:

```text
                 ┌────────────────┐
                 v                │
DISCOVERED ──> ACTIVE ──► STALE ──┘
    │            │           │
    │            v           v
    └────────> EXPIRED <─────┘
```

Valid transitions:

```text
DISCOVERED→ACTIVE
DISCOVERED→EXPIRED
ACTIVE→STALE
ACTIVE→EXPIRED
STALE→ACTIVE
STALE→EXPIRED
```

* `DISCOVERED` = newly identified job not yet through required validation/ingestion.
* `ACTIVE` = successfully validated as available.
* `STALE` = absent from a successful complete snapshot but not yet confirmed unavailable.
* `EXPIRED` = confirmed unavailable.
* Only `ACTIVE` jobs participate in active retrieval/matching.
* Polling failures **never change lifecycle state**.
* Incremental-source absence never creates `STALE`.
* `STALE → EXPIRED` uses configurable consecutive-missing-snapshot count and/or maximum stale duration; either configured condition may trigger expiration.
* Reliable explicit `source_expires_at` may cause immediate expiration.
* Rediscovery can reactivate `STALE → ACTIVE`.
* Expired jobs are retained; physical deletion is out of MVP.

## Polling

Per-source state:

```text
job_sources:
id, name, type, polling_mode, enabled,
polling_interval, last_run_at, last_success_at,
next_run_at, last_error
```

Flow:

```text
Scheduler
→ acquire source lock
→ poll/fetch
→ validate
→ normalize
→ upsert
→ lifecycle update
→ schedule indexing/embedding
```

Each run distinguishes:

```text
found / created / updated / unchanged / absent-from-complete-snapshot
```

A failed run is never treated as a missing snapshot.

`source_runs` must record enough information to prove whether snapshot-based lifecycle transitions are safe.

Overlapping runs for the same source are prevented through PostgreSQL locking/coordination.

## Indexing

Only `status = ACTIVE` belongs to the active retrieval dataset.

### Text

PostgreSQL Full-Text Search over:

```text
title, company, description, skills, requirements, location
```

Partial indexes may optimize active jobs. "De-indexing" means excluding a job from active retrieval, not necessarily physically removing database index entries.

### Semantic

Job embedding representation:

```text
title + normalized skills + requirements
+ relevant description + location + mode
```

Candidate representation:

```text
job titles + occupations + skills + experience
+ education + certifications + languages + preferences
```

Location/mode may appear in representations but must never become geographic eligibility logic.

Only job embeddings are persisted in pgvector. Candidate embeddings remain in memory.

If the model/version changes:

```text
invalidate embeddings → background regeneration → update/rebuild vector index as needed
```

This must not depend on `content_hash`.

## Matching

1. **Eligibility filters** — hard-exclude only sufficiently certain incompatibilities:
   employment type, seniority, language, clearly mandatory requirements. No geographic filtering.
2. **Textual retrieval** — FTS over skills, titles, occupations, requirements, relevant CV terms and descriptions.
3. **Semantic retrieval** — pgvector similarity. Jobs without a current valid embedding are temporarily excluded from semantic retrieval.
4. **Structured scoring** — skill coverage, seniority, experience, employment type, language. Geographic/location/mode compatibility is excluded.
5. **Ranking** — combine normalized component scores.

Default:

```text
final =
    0.45 * textual_score
  + 0.35 * semantic_score
  + 0.20 * structured_score
```

All components and final score are normalized to `[0,100]`. Weights are configurable.

Uncertain extraction should preferably affect scoring rather than cause hard exclusion.

The final score is a **compatibility score, not an employment probability**.

## MatchResult

```text
job_id, score, eligibility,
textual_score, semantic_score, structured_score,
matched_skills[], missing_requirements[],
embedding_model, algorithm_version
```

`eligibility` means matching eligibility, **not geographic eligibility**.

Component scores may remain internal unless exposed by the API.

## REST API

```text
POST /matches
GET  /health   # optional
```

`POST /matches` receives structured CV JSON and returns ranked recommendations.

Response includes at minimum:

```text
job_id, score, eligibility, matched_skills, missing_requirements
```

and system metadata:

```text
algorithm_version
embedding_model
```

Candidate data must never be persisted or logged, including application/access/request bodies, exceptions, tracing, or telemetry.

FastAPI provides OpenAPI documentation.

## Processing & Scheduler

Background worker handles:

```text
polling
normalization
expiration
text indexing
embedding generation
embedding reprocessing after model changes
```

Scheduler may be bundled into the worker or run separately.

PostgreSQL handles scheduling state, locking, and coordination. Prevent concurrent processing of the same source/conflicting lifecycle operations.

Embedding generation should be asynchronous and must not block ingestion/API requests.

## Database

Persisted entities:

```text
job_sources
source_runs
jobs
skills
job_skills
job_requirements
```

`jobs` maps exactly to the canonical `Job`.

PostgreSQL is the only application-state store. Model files are deployment/cache artifacts.

Database supports:

* normalized jobs
* source identity/change detection
* FTS/vector search
* lifecycle/expiration
* polling state/history
* scheduler/worker coordination

No candidate tables.

## Observability

Record per-source execution:

```text
source_runs:
id, source_id, started_at, finished_at, status,
snapshot_complete, jobs_found, jobs_created,
jobs_updated, lifecycle_changes, errors
```

Also record duration, polling mode, parsing/HTTP/indexing/embedding failures, and matching duration.

Lifecycle changes may be aggregate counts or structured transitions.

## Security & Privacy

* Credentials only through environment variables/secrets.
* HTTPS in production.
* Minimize stored personal data.
* Candidate data is transient and never logged/persisted.
* Restrict database access.
* Apply relevant LGPD principles.
* Production/public candidate-data endpoints require authentication.

## Local Execution

Docker Compose:

```text
PostgreSQL + pgvector
API
Worker
```

Embedding model runs locally and is downloaded once into a persistent volume.

No paid LLM/embedding API, VPS, paid vector DB, or mandatory proprietary service.

## Deployment

Prefer free tiers, GitHub Actions, open-source infrastructure, and PostgreSQL providers supporting pgvector.

Provider choice must be verified for actual:

* persistent PostgreSQL
* pgvector
* scheduled ingestion
* background processing
* local/self-hosted embedding inference

Verify free-tier resource/usage limits at deployment time. Docker Compose remains the reference environment and architecture stays provider-independent.

## Testing

Required:

* unit
* integration
* API
* end-to-end

Unit tests cover normalization, taxonomy, identity, hashing, lifecycle, requirement extraction, filtering, scoring/ranking, and embedding invalidation/regeneration.

Integration tests use deterministic source fixtures:

```text
source → ingestion → normalization → DB → index
```

Live external-source tests are optional/non-blocking for CI.

E2E tests cover:

* source failures
* incremental vs snapshot behavior
* source identity
* changed jobs
* expiration/reactivation
* missing requirements
* similar jobs from different sources without merging
* ranking determinism
* embedding regeneration after content changes
* embedding regeneration after model changes

Maintain a small fixed ranking/matching regression dataset.

No test should expect deduplication or geographic eligibility filtering.

## Roadmap

1. Core domain — Job, DB schema, migrations, lifecycle, hashing
2. Candidate — validation, normalization, taxonomy
3. Ingestion — source interface, polling modes, first source, normalization, source runs, upsert
4. Lifecycle — timestamps, stale/expired, reactivation, failure protection, snapshots, explicit expiration
5. Multiple sources — APIs, ATS, optional web adapters; no dedup
6. Indexing — FTS, local embeddings, pgvector, regeneration
7. Matching — filters, textual/semantic retrieval, structured scoring, ranking, normalization/versioning; no geo filtering
8. API — matches, health, OpenAPI, errors, production auth
9. Quality — complete test suite, regression dataset, model-version migration, no-dedup/no-geo regression tests
10. Deployment — Docker, production configuration, secrets, backups, free-tier deployment, scheduling, monitoring

## Definition of Done

The complete pipeline works:

```text
Structured CV
→ CandidateProfile
→ Job Sources
→ Normalized Jobs
→ Lifecycle
→ FTS + Vector Index
→ Compatibility Filters
→ Text + Semantic Matching
→ Ranking
→ REST Recommendations
```

It must:

* accept structured CV JSON;
* implement ≥1 job source;
* prioritize Brazilian sources without geographic eligibility filtering;
* normalize jobs into the exact canonical `Job`;
* maintain source-specific identity;
* detect content changes;
* regenerate embeddings after content/model changes;
* correctly handle snapshot/incremental lifecycle semantics and polling failures;
* expire and reactivate jobs correctly;
* exclude expired jobs from active retrieval;
* provide FTS + local semantic matching;
* use a local PT/EN-capable embedding model;
* produce deterministic `[0,100]` compatibility scores;
* expose supporting match information;
* version algorithm/model;
* pass unit/integration/API/e2e tests;
* provide OpenAPI documentation;
* run locally without paid LLM/embedding/infrastructure dependencies or dedicated brokers;
* perform no cross-source deduplication/merging;
* perform no geographic eligibility classification/filtering.

## MVP Boundaries

Defer:

```text
deduplication / opportunity merging
geographic eligibility
frontend / accounts
automated applications / ATS submission
CV generation/adaptation / cover letters
sophisticated entity resolution
agents
mandatory LLM
distributed infrastructure / complex queues
indiscriminate crawling
advanced recommendation personalization
```

## Core Goal

**Collect → normalize → lifecycle-manage → index → compare → rank → expose jobs through REST.**

CV-Match is a **job-data and opportunity-retrieval pipeline**, not an interface or application agent. The priority is a clean, current, searchable job database supporting reproducible and measurable matching.
