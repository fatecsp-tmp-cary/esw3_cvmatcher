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

## Unresolved; address before dependent implementation

These are the remaining clarifications for dependent implementation:

1. **APiBR snapshot completeness:** establish whether pagination/scan behavior
   proves a complete covered set before absence can mark jobs stale. The source
   selection record describes absent jobs as stale, while the architecture
   requires a successful complete snapshot. See [ADR-002](../../docs/architecture/decisions/ADR-002-apibr-mvp-source.md).
2. **Group 1 API contract:** confirm whether `POST /matches` is the integration
   route and actual CV serialization/mapping. The proposal was a request
   envelope `{curriculo_id, curriculo}` and response
   `associacoes[]: {curriculo_id, vaga: {id, titulo, empresa, descricao,
   requisitos[], localizacao?, modalidade?, url_candidatura?}}`; the example CV
   fields were illustrative. Confirm response envelope and fields, optional
   vacancy fields, and whether scores/explanations may be returned. Ranking
   order was to be preserved by array order. Treat `curriculo_id` as an opaque
   transient correlation value.
3. **Categorical canonical values:** candidate schema currently accepts free
   text for seniority, proficiency, mode, and employment type; canonical mapping
   is pending job-data decisions (tracked in code as #83). Define values and
   mapping once job data is available.

The source identity decision is resolved: enforce unique `(platform,
source_job_id)` and reject missing or blank IDs. Source identity is per platform
and does not imply cross-source deduplication. APiBR issue state maps `open` to
`ACTIVE` and `closed` to `EXPIRED`.
