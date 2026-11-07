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

- `POST /matches` accepts matching sections from Sistema Currículo's implemented
  preview at commit `66af300`: required UUID `curriculo_id` and required arrays
  `formacoes`, `experiencias`, `projetos`, `competencias`, and `idiomas`. Every
  array may be empty; no additional collection cap is imposed by this contract.
- `curriculo_id` is the only CV identifier and is not restricted to UUID version
  4. Section items have no `id` field; extra item IDs are rejected. The curriculum
  ID is request-scoped and is never persisted, logged, or echoed in the response.
- Education items contain required `instituicao`, `curso`, `nivel`, `status`,
  `inicio`, and nullable `fim`. Institution/course are 1–200 characters. Levels
  are `ensino_fundamental`, `ensino_medio`, `tecnico`, `tecnologo`, `graduacao`,
  `especializacao`, `mestrado`, or `doutorado`; statuses are `em_andamento`,
  `concluido`, or `interrompido`. Completed education requires a non-null `fim`.
  Institution is supplied by the caller; there is no `FATEC-SP` default.
- Experience items contain required nonempty `empresa`, `cargo`, `descricao`,
  `inicio`, and nullable `fim`. Both education and experience periods use ISO
  calendar dates (`YYYY-MM-DD`) and require `fim >= inicio` when non-null.
  `fim` must be present, even when null, as in the preview DTOs. A null experience
  end date represents ongoing employment; an education end date can be an
  expected completion date for `em_andamento`.
- Competencies contain required nonempty `descricao` and free-text `nivel`;
  the preview does not expose competency `categoria`. Languages contain required
  nonempty `idioma` and free-text `nivel`, with no invented proficiency enums.
- Projects contain required `titulo`, `descricao`, and `tecnologias` as strings,
  with lengths 1–200, 1–2000, and 1–300 respectively. Source education/project
  fields reject Unicode control characters; text is trimmed before length checks.
- The request omits preview identity/contact, presentation, and document fields
  (`estudante`, `titulo_versao`, `layout`, `documentos`). Unknown fields are
  rejected. The old integration-document fields, date aliases, defaults,
  proficiency enums, technology arrays, and collection bounds are not supported.
- `limit` is the only query parameter. It defaults to 10 and accepts integers
  from 1 through 100. There is no `offset` parameter.
- The response follows #40: `matches[]` entries contain `rank`, nested `job`,
  `score`, boolean `eligibility`, `matched_skills[]`, `missing_requirements[]`,
  `embedding_model`, and `algorithm_version`. The nested job contains a required
  stable positive integer `id` and the public descriptive fields listed in the
  feature spec. Eligibility never represents geographic eligibility; detail
  arrays are required and may be empty. The API response omits `curriculo_id`.
- `GET /health` returns `{"status":"ok"}`.
- Validation errors never echo submitted keys or values. Each rejected extra
  field produces an `extra_forbidden` error whose `loc` points to the containing
  object, with the arbitrary extra key removed. Known-field errors retain their
  schema field names and list indexes.

### Consolidation decision (2026-11-06)

The user confirmed `POST /matches` in PR #130 as the Grupo 1 integration
route, retaining its `limit` parameter and RFC 9457 errors. The response must
satisfy issue #40 by exposing job identity, eligibility, and match details.

### Source-model decision (2026-11-07)

The user declared the integration document outdated and selected the implemented
preview's field names and dates. The request schema above supersedes the earlier
flat integration-document payload. Source authority is
`code-alchemists-br/sistema-curriculo` commit `66af300`, specifically
`src/backend/api/previa_versao_curriculo.py` for field names/types and
`src/backend/domain/itens_perfil.py` plus `value_objects.py` for validation.
The matching projection excludes identity/contact and presentation fields;
this is an intentional request projection, not the entire preview response.
No alternative field aliases from the outdated document or CRUD API are accepted.
The user subsequently removed section-item IDs from the matching projection;
only `curriculo_id` remains.

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
4. **Existing persistence alignment:** the initial job migration/model already
   exists, but the model adds `source_id` and lacks canonical fields including
   `source_expires_at`, `currency`, `last_verified_at`, `raw`, `embedding`, and
   `content_hash`; its status enum only has `ACTIVE` and `EXPIRED`. This conflicts
   with the exact canonical fields and lifecycle in the architecture and feature
   spec. Resolve before dependent persistence/lifecycle work; this consolidation
   does not change or approve those existing differences.

Do not resolve remaining questions by inference. Record future outcomes in the
relevant specification, architecture/ADR if applicable, plan, and tasks.
