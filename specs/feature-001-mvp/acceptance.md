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
  array may be empty. Service caps are 20 `formacoes`, 50 `experiencias`,
  50 `projetos`, 200 `competencias`, and 20 `idiomas` (ADR-006).
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

PR #111 must build on this request and response contract rather than
restore its `CandidateProfile` request body. The current executor accepts
`CurriculumRequest` and `limit`; transient candidate normalization is implemented in #112; complete pipeline
integration remains pending.

## Restacked implementation decisions (2026-11-07)

The user corrected the delivery graph to one linear stack:
`#130 → #101 → #104 → #105 → #106 → #107 → #108 → #109 → #110 → #111 → #112`.
PR #130 remains exactly at `d305975`; child PRs own their changes and decisions.
The accepted behavioral decisions from the preceding interview are retained.

- [ADR-007](../../docs/architecture/decisions/ADR-007-canonical-persistence-alignment.md)
  resolves source identity and canonical persistence: unique platform/source ID,
  reject blank/missing IDs, SQL-only source configuration metadata, corrective
  migrations and terminal EXPIRED. Description section preservation is approved;
  omit raw payloads until retention rights are established.
- [ADR-003](../../docs/architecture/decisions/ADR-003-apibr-availability-and-partial-runs.md)
  records conservative unknown availability, no default verifier, per-record
  rejection and PARTIAL commits. Network failures roll back job changes; partial
  runs do not advance last_success_at or absence-based lifecycle evidence.
- [ADR-005](../../docs/architecture/decisions/ADR-005-weighted-any-term-fts.md)
  records Portuguese weighted any-term search and its English/accent limitations.
- Category aliases map seniority/mode to shared domain enums; unknown values
  yield no category. Language and employment types remain validated free text.
- [ADR-006](../../docs/architecture/decisions/ADR-006-curriculum-projection-and-bounds.md)
  supersedes uncapped arrays with the service caps above. Align internal
  validation with every valid public request, including empty sections, and
  preserve source dates/levels without carrying the UUID. The public executor
  remains CurriculumRequest plus limit.

## Unresolved; address before dependent implementation

1. Verify actual APiBR payload, scan completeness and source usage/retention
   evidence (#113/#132/#134). A synthetic state-free fixture is not proof of
   the endpoint shape. No unproven scan may mark absent jobs stale.
2. Select and record the CPU-feasible PT/EN embedding model/version and metadata
   before semantic work (#26/#118/#140); preserve the fixed canonical Job fields.
3. Define canonical language/employment requirement mappings and confidence
   before hard exclusion (#139). Arbitrary free text is insufficient evidence.

Implementation status is in [tasks](tasks.md). Unimplemented worker, lifecycle,
matching and operational requirements remain pending; restacking is not an MVP
completion claim.
