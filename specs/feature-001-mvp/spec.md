# Feature 001: CV-Match MVP

## Behavior

The service receives the complete Sistema Currículo CV object, validates it,
adapts it to a request-scoped internal candidate representation, ingests
normalized source-specific jobs,
maintains their lifecycle and search indexes, and returns ranked compatible
jobs through `POST /matches`. CV parsing is external. `GET /health` is optional.

## Candidate request and normalization

`POST /matches` accepts the complete flat JSON body from the Sistema Currículo
Grupo 1 → Grupo 2 integration contract (Contrato 1.0.0/1.1.0); it does not
require a separate `{curriculo_id, curriculo}` envelope. The external schema
is:

```text
curriculo_id: string (required, 8–64 characters; UUID v4 or `cur_`-prefixed opaque ID)
dados_pessoais: {
  cidade?: string (2–60 characters)
  estado?: string (two uppercase UF letters)
  modalidade_preferencial: presencial | remoto | hibrido | indiferente
}
formacao_academica: [{
  curso: string (3–100 characters)
  instituicao?: string (2–100 characters; defaults to FATEC-SP when omitted)
  status: em_andamento | concluido | trancado
  previsao_conclusao?: YYYY or YYYY-MM
}] (at least one)
competencias: [{ nome: string (1–50 characters), nivel: basico | intermediario | avancado }]
  (at least one)
idiomas?: [{ idioma: string (2–40 characters), nivel: basico | intermediario | avancado | fluente }]
experiencias_profissionais?: [{
  cargo: string (2–80 characters)
  empresa: string (2–80 characters)
  descricao?: string (up to 1000 characters)
}]
projetos_academicos?: [{
  titulo: string (3–100 characters)
  tecnologias?: string[]
  descricao?: string (up to 1000 characters)
}]
```

The three optional arrays may be omitted or empty. `curriculo_id` is an opaque
correlation identifier; it must not reveal student identity and is never
persisted or logged. Do not transmit direct identifiers such as a student's
name, CPF/RG, email, phone number, or residential address. Do not accept or
require fields from the former internal
`CandidateProfile` shape (`skills`, `job_titles`, `experience`, `education`,
`preferences`, and similar) directly on the wire.

The validated request is adapted into a transient internal candidate
representation: `competencias[].nome` supplies skill text; its `nivel` is
preserved as candidate evidence; academic formation supplies education data;
professional experience and academic projects supply role/project context;
`idiomas` supplies language evidence; and `dados_pessoais` supplies optional
location and work-arrangement preference. `modalidade_preferencial` is the
request's scalar preference (not the former internal `preferences.modes[]`).
Keep project and education details available to matching rather than
discarding fields that do not fit the former `CandidateProfile` model. The
internal representation is not the API contract.

Map the validated `modalidade_preferencial` values:
`presencial` → `ON_SITE`, `remoto` → `REMOTE`, `hibrido` → `HYBRID`, and
`indiferente` → no work-arrangement preference. Reject values outside this
contract enum. The payload has no explicit candidate seniority,
employment type, or years-of-experience field; do not require or invent those
values. Do not infer a hard seniority exclusion from education or job titles.
Competency levels and language levels are validated source values, but have no
corresponding canonical job fields; preserve them as descriptive matching
evidence and do not use them for hard exclusion.

The exact canonical `Job` field set is defined in the
[architecture overview](../../docs/architecture/overview.md). Its `skills`
field contains normalized skill names. Classified job requirements are
separate records in `job_requirements` (with `REQUIRED`, `PREFERRED`, or
`NICE_TO_HAVE` classification); they are not a `requirements` field on `Job`.
The persistence-only `job_sources` record configures an adapter and polling, while
`platform + source_job_id` identifies a source job. These concepts are related
through persistence but are not interchangeable. Embedding model/version and
ranking algorithm version are configuration/metadata, not `Job` fields.
`source_expires_at` is an explicit source expiration; absence does not imply
expiration. `raw` retention follows source restrictions. Null job embedding
means missing/invalid for the configured model.

## Ingestion and normalization

The source interface exposes asynchronous `discover`, `fetch_jobs`,
`fetch_job`, and synchronous `normalize` operations. Sources declare
`INCREMENTAL` or `SNAPSHOT`; only a successful complete snapshot may make
absence meaningful. Source adapters should provide stable IDs. MVP source:
APiBR (see [ADR-002](../../docs/architecture/decisions/ADR-002-apibr-mvp-source.md)).

Normalize raw job data through source parsing, HTML/whitespace/Unicode cleanup,
section detection, skill/keyword extraction, alias normalization, requirement
classification, then canonical Job. Requirement classes are `REQUIRED`,
`PREFERRED`, and `NICE_TO_HAVE`; detected skills must not automatically be
assumed mandatory. Deterministic dictionaries, aliases, regex, phrase/fuzzy
matching, and section detection are proposed. PostgreSQL FTS handles DB-level
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
`STALE→EXPIRED` uses configured consecutive missing snapshots and/or maximum
stale duration; either configured condition may expire a job. Reliable explicit
`source_expires_at` may expire immediately. Rediscovery reactivates stale jobs.
APiBR aggregates GitHub issues: an issue returned with `state=open` is `ACTIVE`,
and one returned with `state=closed` is `EXPIRED`. Other sources must map their
own availability signals according to their source semantics.
Retain expired records; physical deletion is out of MVP.

`last_seen_at` tracks successful observation; `last_verified_at` tracks
successful fetch/validation under source semantics. A changed normalized content
hash updates the job, reindexes text, nulls its embedding, and schedules
regeneration. Unchanged content is not updated. Model/version changes
independently invalidate and regenerate embeddings.

Only active jobs are in active retrieval. FTS covers title, company, description,
skills, classified job requirements, and location. Semantic job representation
uses title, normalized skills, classified job requirements, relevant
description, location, and `work_arrangement`.
Candidate representation is derived from `competencias`, `formacao_academica`,
`experiencias_profissionais`, `projetos_academicos`, `idiomas`, and the allowed
location/work-arrangement preference. Persist only job embeddings in pgvector;
candidate embeddings stay in memory. Jobs without a
current valid embedding are excluded from semantic retrieval while missing.

## Matching and API

Stages: (1) hard-exclude only clearly mandatory job requirements; the incoming
curriculum has no explicit seniority, years-of-experience, or employment-type
value, and competency and language levels are descriptive evidence, so do not
hard-exclude on those bases; (2) textual FTS;
(3) pgvector similarity; (4) structured skill, education, and
`work_arrangement` scores, with role history, competency levels, and language
text contributing descriptive evidence when available; (5) combine normalized
components. No
geographic filtering/scoring. Uncertain extraction should preferably affect
scoring rather than exclusion.

Default final score is `0.45 * textual + 0.35 * semantic + 0.20 * structured`;
weights are configurable and component/final scores are `[0,100]`. Score means
compatibility, not employment probability. `POST /matches` returns a
top-level `matches[]` ranked in array order. Each item contains only
`rank`, `job`, `score`, `embedding_model`, and `algorithm_version`. `job`
contains the descriptive canonical fields `title`, `company`, `description`,
`keywords`, `skills`, `location`, `work_arrangement`, `seniority_level`,
`salary`, `currency`, `publication_date`, and `job_url`; persistence fields,
raw payloads, embeddings, hashes, platform/source identifiers, and lifecycle
timestamps are excluded. Do not expose component scores or explanations.
The route uses `limit` (default `10`, range `1..100`) and `offset` (default
`0`, minimum `0`) query parameters for result pagination.
Candidate data and `curriculo_id` are opaque/transient and never persisted or
logged. FastAPI provides OpenAPI.

Errors use RFC 9457 `application/problem+json`: `type` is `about:blank`, `title`
is the HTTP phrase, `status` is numeric, `detail` is optional; 422 adds one
`errors` item per invalid field (`loc`, `msg`, `type`). 422 invalid field/JSON;
404/405 unknown route/method (405 includes `Allow`); 503 unavailable required
database/model; 500 generic failure. Bodies/logs omit submitted values and
exception messages; logs include exception type and origin only. Fixed request
schema fields prevent client keys from being echoed in error locations.

## Persistence, processing, operations

Persist `job_sources`, `source_runs`, `jobs`, `skills`, `job_skills`, and
`job_requirements`; no candidate tables. A `job_sources` row stores adapter and
polling configuration; its `name` is not the canonical job `platform` field.
The `source_id` foreign key on persisted jobs links to this configuration and
is excluded from canonical jobs and API payloads. Source state includes `id`,
`name`, `type`, `polling_mode`, `enabled`, `polling_interval`, `last_run_at`,
`last_success_at`, `next_run_at`, and `last_error`. Run records include
`id`, `source_id`, timestamps, status, snapshot completeness, found/created/
updated/lifecycle counts, and errors; capture enough evidence to establish
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
