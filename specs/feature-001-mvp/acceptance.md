# MVP acceptance and clarifications

## Acceptance criteria

- Accept structured CV JSON and validate it into the defined request-scoped
  profile; never persist or log submitted candidate data.
- Ingest at least one selected source through a source adapter and normalize to
  the exact canonical Job fields.
- Preserve `(platform, source_job_id)` source identity and detect content
  changes; do not merge records across sources.
- Correctly distinguish incremental absence, successful complete snapshots,
  and polling failures; apply lifecycle transitions and timestamps safely.
- Retain expired jobs and exclude them from active retrieval; allow stale-job
  reactivation and regenerate embeddings after content or model changes.
- Provide PostgreSQL FTS and local PT/EN-capable semantic search, staged matching,
  deterministic versioned scores in `[0,100]`, and ranked REST recommendations.
- Never use location/mode for geographic eligibility filtering.
- Match agreed API/error contracts, OpenAPI documentation, and operational
  security/privacy constraints.
- Pass relevant unit, integration, API, and end-to-end coverage, including
  ranking regression and no-dedup/no-geographic-filtering cases.

## Resolved API contract

- `POST /matches` accepts the flat Sistema Currículo payload: `curriculo_id`,
  `dados_pessoais`, `formacao_academica`, `competencias`, optional `idiomas`,
  optional `experiencias_profissionais`, and optional `projetos_academicos`.
- At least one academic formation and competency are required. An omitted
  `formacao_academica[].instituicao` defaults to `FATEC-SP`.
- `curriculo_id` is opaque, request-only correlation data. It is never persisted,
  logged, or returned in the response.
- `limit` is the only query parameter. It defaults to 10 and accepts integers
  from 1 through 100. There is no `offset` parameter.
- The response follows #40: `matches[]` entries contain `rank`, nested `job`,
  `score`, boolean `eligibility`, `matched_skills[]`, `missing_requirements[]`,
  `embedding_model`, and `algorithm_version`. The nested job contains a required
  stable positive integer `id` and the public descriptive fields listed in the
  feature spec. Eligibility never represents geographic eligibility; detail
  arrays are required and may be empty. The API response omits `curriculo_id`.
- `GET /health` returns `{"status":"ok"}`.

### Consolidation decision (2026-11-06)

The user confirmed the flat `POST /matches` contract in PR #130 as the agreed
Grupo 1 integration target, retaining its `limit` parameter and RFC 9457 errors.
The response must also satisfy issue #40 by exposing job identity, eligibility,
and match details as specified above. This supersedes the earlier omission of
those public fields. Differing routes and envelopes in Grupo 1 documents are
not adopted by this service; consumer alignment remains external work.

PR #111 must consolidate onto this request and response contract rather than
restore its `CandidateProfile` request body. The current executor accepts
`CurriculumRequest` and `limit`; transient candidate normalization and pipeline
integration remain pending.

## Unresolved; address before dependent implementation

1. **APiBR snapshot completeness:** establish whether pagination/scan behavior
   proves a complete covered set before absence can mark jobs stale. The source
   selection record describes absent jobs as stale, while the architecture
   requires a successful complete snapshot. See [ADR-002](../../docs/architecture/decisions/ADR-002-apibr-mvp-source.md).
2. **Source identity constraint:** reconcile the source-selection record's
   surrogate primary key and `source_job_id` attribute with the planned unique
   `(platform, source_job_id)` constraint. Confirm expected null/duplicate ID
   handling before schema implementation.
3. **Categorical canonical values:** candidate schema currently accepts free
   text for seniority, proficiency, mode, and employment type; canonical mapping
   is pending job-data decisions (tracked in code as #83). Define values and
   mapping once job data is available.

Do not resolve remaining questions by inference. Record future outcomes in the
relevant specification, architecture/ADR if applicable, plan, and tasks.
