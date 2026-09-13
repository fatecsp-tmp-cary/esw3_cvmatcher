# CV-Match — Implementation Plan

## 1. Objective

CV-Match is a REST API for recommending and ranking job opportunities based on a structured CV provided as JSON.

The system must:

* receive a structured CV in JSON;
* collect jobs from public sources;
* restrict ingestion to Brazilian job opportunities;
* normalize jobs into a common schema;
* index the data for efficient search;
* identify and remove expired jobs;
* perform CV × job matching;
* combine textual search and semantic similarity;
* return jobs ordered by compatibility and score.

The MVP must use open-source, free tools that can run locally or on free-tier infrastructure, with no dependency on paid LLM APIs.

The system is exclusively a REST API. The MVP does not include a frontend, automated applications, ATS integration, or CV adaptation.

## 2. MVP Scope

### Included

```text
Structured CV JSON
      ↓
Job Ingestion
      ↓
Normalization
      ↓
Indexing
      ↓
Matching
      ↓
Ranking
      ↓
REST API
```

Features:

* structured CV ingestion;
* Brazilian job collection;
* multiple job sources;
* normalization;
* job lifecycle management;
* job expiration/removal;
* textual indexing;
* local embeddings;
* semantic search;
* CV × job matching;
* compatibility ranking;
* explainable scores;
* unit and integration tests;
* end-to-end testing;
* API documentation.

### Out of Scope

* frontend;
* user registration/interface;
* automated applications;
* ATS integration;
* application submission;
* CV generation or adaptation;
* cover-letter generation;
* mandatory external LLM;
* paid infrastructure.

## 3. Architectural Principles

1. Maintain modular separation between ingestion, normalization, indexing, matching/ranking, and API.
2. Prioritize public APIs and structured sources.
3. Use scraping only when necessary.
4. Isolate each source behind a common interface.
5. Do not couple the domain model to any specific source format.
6. Keep matching independent from the ingestion layer.
7. Separate textual search from semantic similarity.
8. Make ranking deterministic and reproducible.
9. Store enough data for debugging and reprocessing.
10. Avoid proprietary or paid service dependencies.
11. Support fully local execution.
12. Restrict ingestion to Brazilian job opportunities.
13. Respect source terms of use, rate limits, and access rules.

## 4. Architecture

```text
                    Candidate JSON
                         │
                         ▼
                 Candidate Normalizer
                         │
                         ▼
                  Candidate Profile
                         │
                         │
                         ▼
                  ┌──────────────┐
                  │              │
                  │  PostgreSQL  │
                  │  + Indexes   │
                  │  + pgvector  │
                  │              │
                  └──────▲───────┘
                         │
                         │
       ┌─────────────────┴─────────────────┐
       │           Job Ingestion            │
       │                                    │
       │  Public APIs / ATS / RSS / Web     │
       └─────────────────┬─────────────────┘
                         │
                         ▼
                  Job Normalization
                         │
                         ▼
                  Expiration Control
                         │
                         ▼
                     Indexing
                  ┌──────┴──────┐
                  ▼             ▼
             Text Index    Vector Index
                  │             │
                  └──────┬──────┘
                         ▼
                  Matching / Ranking
                         │
                         ▼
                     REST API
```

## 5. Technology

### Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* PostgreSQL

### Indexing

PostgreSQL is the primary data store.

For textual search:

* PostgreSQL Full-Text Search;
* appropriate indexes on searchable fields.

For semantic search:

* pgvector;
* a locally executed open-source embedding model.

### Processing

* Python;
* asynchronous HTTP client;
* scheduler/cron;
* simple worker;
* PostgreSQL for persistence and, if necessary, an initial task queue.

### Testing

* pytest;
* unit tests;
* integration tests;
* API tests;
* end-to-end tests.

### Execution

* Docker;
* Docker Compose;
* local execution;
* free-tier deployment where applicable.

## 6. Project Structure

```text
esw3_cvmatcher/
├── docs/
│   └── reports/
│       └── project-charter.md
|
├── src/
│   ├── api/
│   ├── indexing/
│   │   ├── text/
│   │   └── vector/
│   │
│   ├── ingestion/
|   |   └── worker/
|   │       ├── base/
│   |       ├── sources/
│   │       └── scheduler/
|   |
│   ├── schemas/
│   │   ├── candidate/
│   │   ├── job/
│   │   └── matching/
│   │
│   ├── matching/
│   │   ├── filters/
│   │   ├── textual/
│   │   ├── semantic/
│   │   └── ranking/
│   │
│   ├── persistence/
│   │   └── job/
|   |
│   └── normalization/
│       ├── jobs/
│       ├── skills/
│       └── locations/
│   
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
|
├── docker/
├── docker-compose.yml
├── migrations/
├── scripts/
├── README.md
└── pyproject.toml
```

`models/` contains only persisted job domain and database models. The
`models/job/` package represents jobs and their persisted relationships.

`schemas/` contains Pydantic and request-scoped representations. Candidate
profiles, candidate embeddings, match results, and match responses are created
in memory and are never persisted.

## 7. Candidate Module

The system receives the CV already structured as JSON.

The application must convert this JSON into an internal representation independent of the input format.

```text
Candidate JSON
      ↓
Schema Validation
      ↓
CandidateNormalizer
      ↓
CandidateProfile
```

The input and normalized profile schemas belong in `schemas/candidate/`.
CandidateProfile exists only for the duration of the matching request and is
never persisted or logged.

The profile should represent, when available:

```text
CandidateProfile
├── skills[]
├── job_titles[]
├── occupations[]
├── experience[]
├── education[]
├── certifications[]
├── languages[]
├── locations[]
├── seniority
├── years_experience
└── preferences
```

The normalized profile must be usable by both textual and semantic search. It
must not introduce a candidate database model or candidate table.

## 8. Job Ingestion

Ingestion must be modular and independent from the API.

Conceptual interface:

```python
class JobSource:
    async def discover(self):
        ...

    async def fetch_jobs(self):
        ...

    async def fetch_job(self, job_id):
        ...

    def normalize(self, raw_job):
        ...
```

Possible sources:

```text
JobSource
├── PublicAPI
├── Greenhouse
├── Lever
├── Ashby
├── RSS
└── GenericWebSource
```

The initial implementation should prioritize public and structured sources.

Generic scraping should be used as a fallback.

## 9. Geographic Restriction

The platform must collect Brazilian job opportunities exclusively.

Normalization must identify:

* country;
* state;
* city;
* remote status;
* location declared by the job.

The Brazilian filter should be applied during ingestion/normalization, preventing out-of-scope opportunities from entering the final index.

Remote jobs must be evaluated according to their geographic eligibility. A job marked only as "remote" must not automatically be considered Brazilian without evidence that candidates in Brazil are eligible.

## 10. Canonical Job Model

All sources must produce the same internal model.

```text
Job
├── id
├── source
├── source_job_id
├── company
├── title
├── description
├── location
├── mode
├── salary
├── currency
├── employment_type
├── requirements
├── published_at
      ├── expires_at
├── first_seen_at
├── last_seen_at
├── last_verified_at
├── status
├── canonical_url
├── raw
├── embeddings
└── content_hash
```

The original source payload should be preserved whenever possible for debugging and reprocessing.

## 11. Job Lifecycle

Jobs must have an explicit lifecycle:

```text
DISCOVERED
    ↓
ACTIVE
    ↓
STALE
    ↓
EXPIRED
```

States:

* `DISCOVERED`: newly identified job;
* `ACTIVE`: confirmed as available;
* `STALE`: temporarily not found;
* `EXPIRED`: confirmed unavailable.

A job must not be marked as expired solely because a polling operation failed.

Example:

```text
Polling failure
      ↓
Record failure
      ↓
Keep existing jobs active
```

Expiration should occur only after confirmed absence from successful polling runs or through a reliable `expires_at` value.

## 12. Polling

Each source should have its own configuration:

```text
job_sources
├── id
├── name
├── type
├── enabled
├── polling_interval
├── last_run_at
├── last_success_at
├── next_run_at
└── last_error
```

Flow:

```text
Scheduler
    ↓
Poll source
    ↓
Fetch
    ↓
Validate
    ↓
Normalize
    ↓
Upsert
    ↓
Update lifecycle
    ↓
Index changed jobs
```

Failures must be recorded separately and must not invalidate previously collected data.

## 13. Skill Taxonomy

Create a canonical skill taxonomy.

```text
skills
├── id
├── canonical_name
├── category
├── parent_skill_id
└── aliases
```

Examples:

```text
Kubernetes
├── k8s
└── kube

PostgreSQL
├── Postgres
└── PostgreSQL

JavaScript
├── JS
└── ECMAScript
```

The same taxonomy must be applied to both candidates and jobs.

This reduces false negatives caused by naming differences.

## 14. Job Normalization

Normalization must transform unstructured job text into searchable data.

Initial pipeline:

```text
Job Description
      ↓
Text normalization
      ↓
Section detection
      ↓
Skill/keyword extraction
      ↓
Alias normalization
      ↓
Structured requirements
```

Detect, when possible:

```text
Required
Must have
Requirements

Preferred
Nice to have
Bonus
Plus
```

Requirements may be classified as:

```text
REQUIRED
PREFERRED
NICE_TO_HAVE
```

Initial extraction should use deterministic techniques such as:

* dictionaries;
* aliases;
* regular expressions;
* phrase matching;
* fuzzy matching;
* section detection.

## 15. Indexing

Indexing is a dedicated component of the architecture.

### Textual Index

Use PostgreSQL Full-Text Search to index fields such as:

* title;
* company;
* description;
* skills;
* requirements;
* location.

Create appropriate indexes for efficient search.

### Semantic Index

Use:

```text
CandidateProfile
      ↓
Local embedding model
      ↓
request-scoped candidate embedding
```

and:

```text
Job
 ↓
Local embedding model
 ↓
job_embedding
```

Vectors are stored in PostgreSQL using pgvector.

Only job embeddings are persisted. Candidate embeddings are generated in
memory for the request and discarded after matching.

No external embedding API should be required.

## 16. Matching

Matching combines two retrieval mechanisms:

```text
Candidate
    │
    ├──────────────► Text Search
    │
    └──────────────► Semantic Search
                          │
                          ▼
                   Candidate Jobs
                          │
                          ▼
                       Ranking
```

### Stage 1 — Filters

Remove clear incompatibilities:

* location;
* remote eligibility;
* employment type;
* seniority;
* language;
* mandatory requirements.

### Stage 2 — Textual Search

Match:

* skills;
* titles;
* occupations;
* requirements;
* relevant CV terms;
* job descriptions.

### Stage 3 — Semantic Similarity

Use local embeddings to identify conceptual compatibility even when the exact terms differ.

### Stage 4 — Ranking

Combine textual and semantic results into a final compatibility score.

Example:

```text
final_score =
    0.45 * textual_score
  + 0.35 * semantic_score
  + 0.20 * structured_score
```

Weights must be configurable and may later be adjusted based on evaluation results.

The algorithm version must be stored so that rankings remain reproducible.

## 17. Match Result

The internal result should contain:

```text
MatchResult
├── job_id
├── score
├── eligibility
├── textual_score
├── semantic_score
├── structured_score
├── matched_skills[]
├── missing_requirements[]
└── algorithm_version
```

The API must return jobs ordered by score.

Example:

```json
{
  "job_id": "123",
  "score": 91.4,
  "eligibility": "PASS",
  "matched_skills": [
    "Linux",
    "Python",
    "Docker"
  ],
  "missing_requirements": [
    "AWS"
  ]
}
```

## 18. REST API

The API receives a structured CV, processes it in memory, and returns ranked job recommendations. Candidate information is not persisted.

Initial endpoint:

```text
POST /matches
```

Input:

```json
{
  "candidate": {
    "skills": ["Python", "Docker"],
    "job_titles": ["Backend Developer"],
    "experience": [],
    "education": [],
    "languages": ["Portuguese", "English"],
    "locations": ["São Paulo, SP"],
    "seniority": "mid",
    "years_experience": 3,
    "preferences": {}
  },
  "limit": 20
}
```

Output:

```json
{
  "results": [
    {
      "job_id": "job-001",
      "score": 91.4,
      "eligibility": "PASS",
      "matched_skills": ["Python", "Docker"],
      "missing_requirements": []
    }
  ],
  "algorithm_version": "v1"
}
```

Candidate data must be used only during request processing and must not be
stored in the database or written to logs.

Candidate profiles, candidate embeddings, and match results are not persisted.

The API must be documented through the OpenAPI specification generated by FastAPI.

## 19. Processing and Scheduler

Asynchronous processing should handle:

```text
job polling
job normalization
expiration
indexing
embedding generation
```

Initially:

```text
Scheduler
    ↓
Worker
    ↓
PostgreSQL
```

Do not initially introduce Kafka, RabbitMQ, or Redis without an actual requirement.

## 20. Database

Primary entities:

```text
job_sources
source_runs

jobs
skills
job_skills
job_requirements

embeddings
```

The database must support:

* normalized data storage;
* textual search;
* vector storage/search;
* source polling and lifecycle tracking.

Candidate profiles, candidate embeddings, matches, and match explanations are
request-scoped and must not be persisted.

## 21. Testing

The MVP must have three levels of testing.

### Unit Tests

Test independently:

* CV normalization;
* job normalization;
* skill taxonomy;
* lifecycle;
* requirement extraction;
* filters;
* scoring;
* ranking.

### Integration Tests

Test:

```text
Source
  ↓
Ingestion
  ↓
Normalization
  ↓
Database
  ↓
Index
```

The Resume API adapter should also have integration coverage.

### End-to-End Tests

Validate the complete flow:

```text
Candidate JSON
      ↓
CandidateProfile
      ↓
Job Ingestion
      ↓
Normalized Jobs
      ↓
Indexing
      ↓
Matching
      ↓
Ranking
      ↓
REST Response
```

## 22. Observability

Record:

* execution of each source;
* duration;
* number of jobs found;
* new jobs;
* updated jobs;
* expired jobs;
* parsing errors;
* HTTP errors;
* indexing errors;
* embedding failures;
* matching duration.

Each source execution should have a record:

```text
source_runs
├── id
├── source_id
├── started_at
├── finished_at
├── status
├── jobs_found
├── jobs_created
├── jobs_updated
├── jobs_expired
└── errors
```

## 23. Security and Privacy

CVs may contain personal data.

Minimum requirements:

* never store credentials in source code;
* use environment variables/secrets;
* use HTTPS in deployment;
* minimize stored personal information;
* CV data is transient and must not be logged or persisted;
* authenticate endpoints handling candidate data;
* restrict database access;
* consider LGPD principles.

## 24. Local Execution

The project must run entirely through Docker Compose:

```text
docker-compose
├── PostgreSQL + pgvector
├── API
└── Worker
```

The embedding model must be executable locally.

Local execution must not require:

* paid LLM APIs;
* paid embedding APIs;
* VPS;
* paid vector databases;
* mandatory proprietary services.

## 25. Deployment

If deployment is required for the MVP, prioritize:

* free tiers;
* serverless services;
* GitHub Actions;
* free PostgreSQL;
* open-source infrastructure.

The architecture must remain provider-independent.

Free-tier limits must be verified at deployment time.

## 26. Roadmap

### Phase 1 — Core Domain

* [ ] Job
* [ ] PostgreSQL schema
* [ ] migrations

### Phase 2 — Candidate

* [ ] JSON validation
* [ ] CandidateNormalizer
* [ ] Skill normalization

### Phase 3 — Ingestion

* [ ] JobSource interface
* [ ] First public source
* [ ] Job normalization
* [ ] Source-run tracking
* [ ] Polling

### Phase 4 — Lifecycle

* [ ] `first_seen_at`
* [ ] `last_seen_at`
* [ ] STALE
* [ ] EXPIRED
* [ ] Failure protection

### Phase 5 — Multiple Sources

* [ ] Additional public APIs
* [ ] ATS sources
* [ ] RSS
* [ ] Generic web source

### Phase 6 — Indexing

* [ ] PostgreSQL Full-Text Search
* [ ] Search indexes
* [ ] Local embedding model
* [ ] pgvector
* [ ] Vector indexes

### Phase 7 — Matching

* [ ] Hard filters
* [ ] Textual matching
* [ ] Semantic matching
* [ ] Combined ranking
* [ ] Explainable score
* [ ] Algorithm versioning

### Phase 8 — API

* [ ] Candidate endpoints
* [ ] Job endpoints
* [ ] Matching endpoints
* [ ] OpenAPI documentation
* [ ] Error handling

### Phase 9 — Quality

* [ ] Unit tests
* [ ] Integration tests
* [ ] End-to-end test
* [ ] Source failure tests
* [ ] Expiration tests
* [ ] Matching/ranking test dataset

### Phase 10 — Deployment

* [ ] Docker
* [ ] Production configuration
* [ ] Secrets
* [ ] Database backup
* [ ] Free-tier deployment
* [ ] Scheduled ingestion
* [ ] Monitoring

## 27. Definition of Done

The MVP is complete when it can execute:

```text
Structured CV JSON
       ↓
Candidate Profile
       ↓
Brazilian Job Sources
       ↓
Normalized Jobs
      ↓
Lifecycle Management
       ↓
Text Index + Vector Index
       ↓
Textual Matching
       +
Semantic Matching
       ↓
Ranking
       ↓
REST API
       ↓
Ordered Job Recommendations
```

And satisfies the following criteria:

* [ ] accepts a structured CV;
* [ ] collects Brazilian jobs;
* [ ] supports multiple sources;
* [ ] normalizes job data;
* [ ] detects/removes expired jobs;
* [ ] provides textual search;
* [ ] provides local semantic similarity;
* [ ] ranks jobs by compatibility;
* [ ] returns a score;
* [ ] provides information supporting the score;
* [ ] has unit tests;
* [ ] has integration tests;
* [ ] has an end-to-end test;
* [ ] has REST/OpenAPI documentation;
* [ ] runs locally;
* [ ] does not depend on paid LLMs;
* [ ] does not require paid infrastructure.

## 28. MVP Boundaries

The MVP should remain deliberately focused.

Do not implement before validating the core:

* frontend;
* automated applications;
* ATS application integration;
* CV generation;
* CV adaptation;
* cover letters;
* job deduplication;
* agents;
* mandatory LLM;
* distributed infrastructure;
* complex queues;
* indiscriminate web crawling.

The objective is exclusively to validate the ability to:

**collect → normalize → index → compare → rank → expose Brazilian job opportunities through a REST API.**

## 29. Central Principle

The architecture should treat CV-Match as a **job-data and opportunity-retrieval pipeline**, rather than an interface or application agent.

The priority is to build a clean, up-to-date, searchable database of Brazilian job opportunities on top of which textual and semantic matching can produce reproducible and measurable recommendations.
