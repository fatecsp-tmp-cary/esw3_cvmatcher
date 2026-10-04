# MVP Source Selection

## Selected Source

**Gupy** was selected as the primary data source for the MVP. It provides a stable, well-documented API, consistent job listing structure, and reliable pagination, making it the most suitable option for the initial integration.

Full endpoint specifications, request/response schemas, and the technical comparison matrix for all sources evaluated are documented in [`docs/data/APIs_normalization.md`](./APIs_normalization.md) and are not duplicated here.

## Alternatives Evaluated

The following sources were evaluated as part of the source selection process (see `docs/data/APIs_normalization.md` for full technical details):

- **Meu Padrinho** — initially considered, but testing revealed a critical pagination limitation: the `page` parameter is 0-indexed, and any request with `page >= 1` returns HTTP 204 (no content). Parameters such as `offset`, `limit`, and `pagina` are ignored. The only functional filter is `niveis`, which returns an additional ~10 jobs per level. As a result, only a small fraction of the ~27,600 listed jobs is actually accessible through the API. Due to this limitation, Meu Padrinho was not selected as the primary source for the MVP.
- **InHire**, **Solides**, **Trampos.co**, and **Quero Vagas Tech** — evaluated and documented in `docs/data/APIs_normalization.md`; not selected as the primary source for the MVP.

## Polling / Scanning Mode

The ingestion pipeline follows a periodic scan approach:

1. Fetch the job listing endpoint for the selected source.
2. For each job, fetch detail/skills information as needed.
3. Normalize the data according to the shared schema.
4. Upsert each job record using its unique job identifier.
5. Jobs no longer present in a subsequent scan are marked as `INACTIVE`.

This approach avoids relying on real-time webhooks and keeps the dataset up to date through scheduled polling.

## Limitations and Restrictions

- No candidate profile data or match results are persisted or logged, per `PLAN.md`.
- No deduplication of jobs across multiple sources is performed, per `PLAN.md`.
- No geographic eligibility filtering is applied, per `PLAN.md`.
- All requests respect the source's rate limits, terms of use, and access restrictions, per `CONTRIBUTING.md`.
- Meu Padrinho's pagination limitation (described above) restricts its usability as a complete data source; it may be revisited as a complementary/limited source in future iterations.
