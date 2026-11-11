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
  preview: required UUID `curriculo_id` and required arrays
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
  rejected. Alternative field aliases, defaults, proficiency enums, and technology
  arrays are not supported.
- `limit` is the only query parameter. It defaults to 10 and accepts integers
  from 1 through 100. There is no `offset` parameter.
- `matches[]` entries contain `rank`, nested `job`,
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

### Source authority

The matching projection uses Sistema Currículo's preview field names and
validation from `code-alchemists-br/sistema-curriculo`:
`src/backend/api/previa_versao_curriculo.py` defines field names/types;
`src/backend/domain/itens_perfil.py` and `value_objects.py` define validation.
The request excludes identity/contact and presentation fields.

The executor accepts `CurriculumRequest` and `limit`.
Transient normalization is implemented by `normalize_curriculum` into an immutable
`NormalizedCandidate`, preserving section order, all text, dates, proficiency,
education level/status and projects, while excluding the UUID. This projection
adds no collection/text caps and accepts empty sections. Complete pipeline
integration remains pending; the legacy `CandidateProfile` is not used as a
second public-input validator.

## Implementation decisions

- [ADR-007](../../docs/architecture/decisions/ADR-007-canonical-persistence-alignment.md)
  resolves source identity and canonical persistence: unique platform/source ID,
  reject blank/missing IDs, SQL-only source configuration metadata, corrective
  migrations and terminal EXPIRED. Preserve description sections;
  omit raw payloads until retention rights are established.
- [ADR-003](../../docs/architecture/decisions/ADR-003-apibr-availability-and-partial-runs.md)
  records conservative unknown availability, no default verifier, per-record
  rejection and PARTIAL commits. Network failures roll back job changes; partial
  runs do not advance last_success_at or absence-based lifecycle evidence.

## Unresolved; address before dependent implementation

1. Verify actual APiBR payload, scan completeness and source usage/retention
   evidence (#113/#132/#134). A synthetic state-free fixture is not proof of
   the endpoint shape. No unproven scan may mark absent jobs stale.
2. Select and record the CPU-feasible PT/EN embedding model/version and metadata
   before semantic work (#26/#118/#140); preserve the fixed canonical Job fields.
3. Define canonical language/employment requirement mappings and confidence
   before hard exclusion (#139). Arbitrary free text is insufficient evidence.

Implementation status is in [tasks](tasks.md). Unimplemented worker, lifecycle,
matching and operational requirements remain pending.

## Extraction, contract stability and semantic evidence

Authority: [ADR-008](../../docs/architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md).

- Job extraction uses local GLiNER plus validated taxonomy/aliases and contextual
  requirement classification. Check complete chunk coverage, overlap deduplication,
  conflicts, unknown evidence and extraction-version reprocessing on offline PT/EN
  fixtures. Set quality/runtime targets before production enablement.
- Contract regressions must preserve the accepted Sistema Currículo request,
  query, response and privacy-safe errors, including previously valid payloads.
  Extraction/scoring must not add mandatory fields or tighten validation limits.
- For each job, score every experience title/description and education entry
  semantically. Select the three highest-scoring experiences before recency
  weighting, and the highest-scoring education entry. Changing jobs may change
  which experiences/education are selected.
- Regressions cover a relevant older experience beating an irrelevant recent one
  in selection; greater recency weight among selected experiences; education chosen
  by semantic relevance; ties; 0–2 experiences; empty sections; and repeatability.
  Internal evidence/embeddings and the curriculum UUID never persist or leak into
  responses/logs. Keep component/final scores in [0,100].

### Pending implementation decisions

- The implementation interview selected initial semantic mixing weights of
  **80% experience / 20% education**, subject to validation on reviewed examples.
  See [scoring policy](../../docs/match/scoring-policy.md).
  Recency grouping uses initial weights **1.5 / 1.25 / 1.0**, with equal recency
  receiving equal weight. Similarity calibration and release validation remain
  pending; the aggregation primitive is implemented but not wired to inference.
- Select the pinned GLiNER revision, label set, confidence/quality/runtime targets,
  supporting evidence storage and extraction retry/reprocessing policy.
- The pending collection-cap work conflicts with freezing the currently uncapped
  contract above. Do not add caps to this contract implicitly; reconcile any
  accepted cap decision on another branch with the frozen baseline before merging
  or implementing it. New restrictions require an explicitly approved versioned
  contract. This documentation change does not select a different baseline.

## Docker Compose deployment acceptance

- A clean configured host can build/start the production API, worker/scheduler
  and PostgreSQL+pgvector using the documented Compose procedure.
- Migrations and database/model readiness complete before matching is ready;
  startup failures are visible and do not silently serve incompatible data.
- An end-to-end smoke test exercises fixture ingestion, background processing
  and the production matching response under the immutable public contract.
- Container replacement/restart preserves jobs, source state and model caches;
  shutdown does not remove data volumes. Backup/restore is exercised on test data.
- Deployment documentation covers configuration/secrets, migrations, readiness,
  model preparation, updates and recovery; public deployment retains the specified
  HTTPS, global rate-limit and database-access protections (authentication is
  intentionally absent under ADR-009).

See [deployment behavior](spec.md#docker-compose-deployment). These are pending
release checks, not claims about the existing database-only or mock Compose files.

## Implementation interview: readiness and performance

- Withhold jobs from every matching path until extraction succeeds. Extraction
  failure is not an availability transition. After three failed attempts, record
  failure, emit a structured local error log and require explicit retry.
  No email/webhook alert integration is required. Details and remaining
  operational decisions are in the [extraction policy](../../docs/data/job-field-extraction.md).
- Warm CPU `POST /matches` target: at most five seconds for 10 experiences,
  5 education entries, 10,000 active jobs, limit=10, one request at a time.
  This is an acceptance target awaiting measurement, not a result or public cap.

- The interview selected a mandatory-classification quality gate of at least
  **95% precision and 80% recall** on independently reviewed examples before
  extraction may cause exclusion. Minimum sample counts and threshold tuning
  remain pending; these are acceptance targets, not measured results.

## Production caller boundary

The user selected backend-only, server-to-server calls from Sistema Currículo.
Browser CORS is disabled; no browser login flow is required. The user selected
no authentication and a global 60-requests/minute rolling admission limit; HTTPS
remains required. All API replicas share PostgreSQL admission state. Excess
returns 429 with Retry-After: 60; unavailable admission state returns 503. See
[service access](../../docs/architecture/service-access.md).

## Pre-production clarification

No production deployment exists. The user accepts availability interruptions and
simple stop/reprocess/restart for model/configuration changes; no dual-version
or rolling-cutover consistency mechanism is required. The corrected global quota
is **60 requests per minute**, not per second. See
[ADR-010](../../docs/architecture/decisions/ADR-010-preproduction-and-minute-rate-limit.md).
