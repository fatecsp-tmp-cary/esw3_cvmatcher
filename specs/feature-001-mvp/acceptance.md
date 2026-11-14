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
adds no collection/text caps and accepts empty sections. The matching pipeline
uses this projection; production API composition remains pending in stack PR #175.
The legacy `CandidateProfile` must not become a second public-input validator.

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

1. A live shape probe observed state-free APiBR records. The later ADR-013/count
   probe establishes the approved best-effort completeness
   policy; source usage/retention evidence remains #134. The earlier shape probe
   proves neither availability nor completeness. No hidden verifier is enabled
   and no unproven scan may mark absent jobs stale.
2. The pinned multilingual E5 model/version and separate provenance are implemented in stack PR #171
   (#26/#118/#140); empirical calibration/release approval remains pending. Preserve
   the fixed canonical Job fields.
3. ADR-012 defines conservative canonical language/employment mappings (#139).
   Arbitrary free text remains insufficient evidence; new hard exclusions stay
   disabled until review. Implementation and verification are tracked in tasks.

Implementation status and remaining operational/quality release checks are in
[tasks](tasks.md); implemented services are not evidence of completed deployment.

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
  pending; the deterministic aggregation primitive is implemented in #173 and
  request-scoped inference/retrieval/scoring in #174. Production API composition
  remains pending in #175 and calibration remains provisional.
- Pinned GLiNER revision/labels, provisional confidence, separate evidence storage
  and bounded retry/reprocessing are implemented; see [local GLiNER](../../docs/data/local-gliner.md).
  Mandatory exclusion remains disabled until independently measured quality and
  sample sufficiency are approved.
- Existing ADR-008 authority supersedes ADR-006 collection caps and any internal
  bounds rejecting valid public input. Preserve both projection APIs and lossless
  source sections. [ADR-011](../../docs/architecture/decisions/ADR-011-main-integration-compatibility.md)
  records this reconciliation without a new decision; historical ADRs stay unchanged.

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

See [deployment behavior](spec.md#docker-compose-deployment). The pinned offline Compose smoke is historical evidence from the original
integration after main reconciliation, including worker/API processing, replacement
durability and backup/restore. It has not been rerun for this branch; current-head
Compose acceptance remains pending.
Evidence and remaining release checks are tracked in [tasks](tasks.md).

## Implementation interview: readiness and performance

- Withhold jobs from every matching path until extraction succeeds. Extraction
  failure is not an availability transition. After three failed attempts, record
  failure, emit a structured local error log and require explicit retry.
  No email/webhook alert integration is required. Details and remaining
  operational decisions are in the [extraction policy](../../docs/data/job-field-extraction.md).
- Warm CPU `POST /matches` target: at most five seconds for 10 experiences,
  5 education entries, 10,000 active jobs, limit=10, one request at a time.
  The isolated reconciled synthetic reference met this target; see [tasks](tasks.md).
  Generalization remains unproven; this workload is not a public cap.

- The interview selected a mandatory-classification quality gate of at least
  **95% precision and 80% recall** on independently reviewed examples before
  extraction may cause exclusion. The sample/partition policy is resolved in ADR-012; threshold tuning awaits
  reviewed calibration cases. These are targets, not measured results.

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

## Main integration compatibility checks

Preserve ADR-004/005 Portuguese any-term FTS weights (A title/skills; B
company/keywords/normalized requirements; D description/location), JSON text
rendering and publication-date-descending then platform/source-ID ties. Verify
successful current extraction on every retrieval path and unchanged final
0.45/0.35/0.20 blend. Retain taxonomy persistence/category aliases and both
projection APIs; no valid public input may fail superseded internal caps.
See [ADR-011](../../docs/architecture/decisions/ADR-011-main-integration-compatibility.md).

## Issue-completion interview (2026-11-12)

[ADR-012](../../docs/architecture/decisions/ADR-012-issue-completion-and-evaluation-policy.md)
resolves the previously pending mapping, processing-budget, sample/partition,
quality-target and deployment-scope decisions. The minimum reviewed corpus is
40 PT/10 EN, divided into 20 PT/5 EN calibration and 20 PT/5 EN held-out cases.
Span targets are 90% precision/80% recall per language; mandatory classification
retains 95% precision/80% recall. Semantic role AUC must reach 0.90 and accuracy
80% per language on held-out cases. The user is the human reviewer. No policy
choice or annotation alone establishes a passing quality measurement.

Structured scoring uses equal weights across comparable available dimensions;
unknown values never exclude and employment preferences are never inferred.
New hard exclusions remain disabled until review. Matching has one process-local
slot, no waiting queue, privacy-safe 503 overload and a 30-second cooperative
deadline. In-flight native calls can finish before cancellation is observed;
this introduces no public payload caps. Global admission remains 60/minute.
Deployment acceptance here is local pre-production; external HTTPS/provider
acceptance remains separately tracked in #150.

### Resolved snapshot coverage clarification

[ADR-013](../../docs/architecture/decisions/ADR-013-best-effort-apibr-snapshot-attestation.md)
records the user's accepted best-effort health/count completeness rule: healthy
unchanged count/timestamp before/after, exact distinct ID count, a terminal empty
page and no duplicates/rejections/request failures. Explicit SNAPSHOT configurations
alone may qualify; missing health/incremental scans stay incomplete. This is not
an atomic proof. Qualifying scans still do not invent availability or execute the
separate #145 absence/expiration policy. The #125 regression criterion covers both
qualifying/incomplete attestations and these conservative lifecycle protections.

## Extraction correction acceptance (issue #116 / PR #170)

Authority: [ADR-018](../../docs/architecture/decisions/ADR-018-extraction-context-and-approximate-evidence.md).

- Regress multiple clause strengths, local-over-heading precedence, negated and
  affirmative occurrences, PT/EN cue variants, PREFERRED versus NICE_TO_HAVE,
  strongest occurrence selection and retained conflict/negation/approximation flags.
- Retain detected-but-unclassified evidence. Select requirements separately from
  company/benefits/application/background text; test repeated explicit requirements,
  missing/malformed sections, credential/multiword wrappers and exact Unicode offsets.
- Regress typo tolerance on both job and candidate evidence: minimum five characters,
  at most one edit including adjacent transposition, unique closest concept, exact
  aliases first, preserved punctuation/short names, no permanent alias creation.
- Keep empty candidate/no requirement cases in role metrics under explicit
  evidence-based labels. Preserve zero semantic evidence and no all-empty matches.
- Run focused extraction tests, relevant full unit/integration suites and offline
  calibration only before freezing extraction/configuration and calibration/cutoff.
  Preserve failures and case errors; report PT/EN separately.
- Keep original reviewed labels/results. Record authorized policy updates in new
  copies. The diagnosed held-out set is regression material; independent acceptance
  remains pending a fresh blind review. Keep ADR-012 numeric gates and score-only
  behavior. Additional mandatory sample minimums remain a future exclusion decision.

## Bilingual search interview — issues #147/#159

Authority: [ADR-022](../../docs/architecture/decisions/ADR-022-bilingual-ascii-search-and-fuzzy-fallback.md).

Implement and compare the approved separate projection, bilingual retrieval and fuzzy fallback; verify readiness, symbol distinctions, original offsets, group priority, limits and index/rebuild impact. No current implementation completion is claimed.

## Mandatory coverage interview — issue #120

Authority: [ADR-021](../../docs/architecture/decisions/ADR-021-mandatory-coverage-score-only.md).

Implement/version per-job coverage and its boundary/evidence tests without changing eligibility, DTOs, existing blend weights or evaluation sample requirements.

## Concurrent source-identity persistence

- Concurrent inserts/updates preserve unique platform/source identity, content
  hashes, terminal expiration and refreshed committed lifecycle evidence.
- Reversed overlapping APiBR scans complete without deadlock. All remote page
  fetches precede identity locking; batch locks use a deterministic order and
  no more than 256 stripes regardless of record count.
- Per-record malformed data remains isolated. Unexpected persistence failure
  rolls back every job change in that scan and records a failed run.

These incremental regressions are recorded in the
[PR #167 review](../../docs/reports/2026-11-14-pr167-review.md).


## Explicit source-timestamp expiration

Due reliable source expiry expires nonterminal records once, preserves retained
history and first/last observation plus verification timestamps, and remains
terminal when ingestion runs concurrently. Ambiguous expiry/clock representations
are rejected. A partial due-time index agrees with migrated PostgreSQL metadata.
See the [PR #169 review](../../docs/reports/2026-11-14-pr169-review.md).


## PR #171 embedding maintenance acceptance

Equivalent normalized location objects must produce identical passages despite
JSON key insertion order. Current normalized requirements participate in passages;
changed extraction/model/passage-policy versions invalidate prior vectors.
Independent-connection tests must preserve skip-locked claims without locking Job
rows, and preparation must set telemetry configuration before importing the hub.
Current-head verification is recorded in the
[PR #171 review](../../docs/reports/2026-11-14-pr171-review.md).


## PR #173 scoring regressions

Ranking configuration rejects non-integer and nonpositive retrieval counts before
SQL retrieval. Semantic aggregation normalizes over available sections even for
extreme positive finite weight ratios; a missing section cannot erase the other
section's evidence. Defaults and final blend remain unchanged. See the
[review record](../../docs/reports/2026-11-14-pr173-review.md).

## Request-scoped matching pipeline verification

- Empty curricula return no matches before encoding or database access. Without
  experience/education, no semantic query is invented from other sections; actual
  textual evidence remains eligible for textual/structured scoring.
- Textual/semantic union deduplicates persisted job IDs. Only active jobs with
  current extraction pass; semantic evidence also requires current model, content,
  extraction and valid vector dimensions. Recheck final textual/vector evidence
  so stale pool hits cannot become unscored recommendations.
- Invalid encoder counts/vectors fail explicitly. Final scores/order/ranks remain
  deterministic; candidate identity/content stay out of logs and responses, and
  contrasting job locations/modes never create geographic eligibility exclusions.

See the [PR #174 review](../../docs/reports/2026-11-14-pr174-review.md) for scoped
verification. Production API composition and release acceptance remain pending.
