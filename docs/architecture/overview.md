# Architecture overview

The intended system separates API, candidate/job schemas, normalization,
source adapters and ingestion, persistence, indexing, and matching/ranking.
Matching is independent from ingestion; source adapters map external payloads to
the canonical job model. Current source layout is smaller than this target;
implementation status is tracked in the [MVP tasks](../../specs/feature-001-mvp/tasks.md).

```text
Structured CV → API/schema → transient candidate normalization ────┐
                                                                   ├→ matching → ranked response
Sources → ingestion → normalization → PostgreSQL jobs → FTS/vector ┘
```

PostgreSQL is the sole application-state store, including polling state and
worker coordination. A lightweight scheduler/worker may be bundled or separate;
no dedicated queue is required. Job embeddings are persisted; candidate
embeddings and match results are request-scoped. The local embedding model is a
deployment/cache artifact. Docker Compose with PostgreSQL + pgvector is the
reference local and single-host deployment environment. The deployment stack
includes the production API, background worker/scheduler and PostgreSQL+pgvector,
with persistent database and local-model cache volumes. Deployment acceptance
is defined in the [MVP spec](../../specs/feature-001-mvp/spec.md#docker-compose-deployment).

The production and mock APIs share public request/response models in
`src/schemas/`. Canonical work-arrangement and seniority enums live in
`src/domain/job.py` and are reused by schemas and persistence, allowing the mock
to run without importing database libraries.

The transient public-request projection lives in
`src/normalization/candidate/curriculum.py`. Its immutable `NormalizedCandidate`
preserves all five source sections without the UUID or additional caps. It is
an intermediate matching representation, not a new public API model. Production
matching integration is pending in stack PR #175; compatibility reconciliation preserves both
projection APIs under [ADR-011](decisions/ADR-011-main-integration-compatibility.md).

The intended canonical `Job` has exactly these fields:

```text
id, platform, source_job_id, source_expires_at, company, title, description,
keywords, skills, location, work_arrangement, seniority_level, salary, currency,
publication_date, first_seen_at, last_seen_at, last_verified_at, status,
job_url, raw, embedding, content_hash
```

`platform + source_job_id` is source identity: `platform` names the upstream
job platform represented by the record. It is not the polling-configuration
record. `job_sources` stores source-adapter/polling configuration, and its
`source_id` foreign key on the SQL `jobs` row is persistence metadata only; it
is not part of the canonical `Job` representation. These values are related by
the persistence layer but are not interchangeable. Additional persisted data
belongs in separate structures. See
[invariants](invariants.md), [ADR index](decisions/README.md), and [MVP
spec](../../specs/feature-001-mvp/spec.md).

Job enrichment uses local GLiNER span extraction before validated canonical
mapping; its version/evidence remain separate metadata. Semantic matching evaluates
individual experiences and education entries, selects the three best-matching
experiences with recency weighting and the best education score per job, while
preserving the public integration contract. See
[ADR-008](decisions/ADR-008-extraction-contract-and-semantic-evidence.md).

The implementation interview requires successful extraction before jobs enter
any matching path. Extraction readiness is supporting state separate from
canonical availability; failures must not change lifecycle. The semantic
aggregation primitive and its provisional coefficients are planned in stack PR #173
(`src/matching/semantic.py` and `../match/scoring-policy.md`). Pinned local inference
is planned in #170–#171 and production executor wiring in #175; calibration
and quality approval remain pending. Portuguese FTS retains ADR-004/005 weights,
JSON text rendering and publication-date/identity ties, with extraction
readiness on every path planned in stack PR #172. Integrated database verification
under ADR-011 is historical evidence from the original integration, not this head.
Taxonomy persistence and category aliases from main remain part of the system.
