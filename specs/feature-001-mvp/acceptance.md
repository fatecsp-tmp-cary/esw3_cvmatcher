# MVP acceptance and clarifications

## Acceptance criteria

- Accept and validate the complete flat Sistema Currículo request object
  (`curriculo_id`, `dados_pessoais`, `formacao_academica`, `competencias`, and
  optional `idiomas`, `experiencias_profissionais`, `projetos_academicos`),
  adapting it to transient matching data without discarding relevant sections;
  never persist or log the submitted curriculum.
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
- Return `matches[]` ranked by array order; each item contains only `rank`,
  descriptive `job`, `score`, `embedding_model`, and `algorithm_version`.
  Match the API/error contract, OpenAPI documentation, and operational
  security/privacy constraints.
- Pass relevant unit, integration, API, and end-to-end coverage, including
  ranking regression and no-dedup/no-geographic-filtering cases.

## Unresolved; address before dependent implementation

These are the remaining clarifications for dependent implementation:

1. **APiBR snapshot completeness:** establish whether pagination/scan behavior
   proves a complete covered set before absence can mark jobs stale. The source
   selection record describes absent jobs as stale, while the architecture
   requires a successful complete snapshot. See [ADR-002](../../docs/architecture/decisions/ADR-002-apibr-mvp-source.md).
The incoming request supplies `modalidade_preferencial`, mapped to the existing
`WorkArrangement` enum. It has no explicit seniority, years-of-experience, or
employment-type field. Its competency and language levels remain descriptive
evidence and must not cause hard exclusion.

The source identity decision is resolved: enforce unique `(platform,
source_job_id)` and reject missing or blank IDs. Source identity is per platform
and does not imply cross-source deduplication. APiBR issue state maps `open` to
`ACTIVE` and `closed` to `EXPIRED`.
