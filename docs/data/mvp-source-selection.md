# MVP Source Selection

## Status

This document reflects the current state of source evaluation for the MVP job ingestion pipeline. The final decision between Gupy and Meu Padrinho is still pending confirmation from the project manager. This document will be updated once the decision is formally approved.
The Definition of Done for this task (selected source, rejected alternatives, polling approach, and limitations) is addressed below, with the exception of the final source selection, which remains pending.

Full endpoint specifications, request/response schemas, and the technical comparison matrix for all sources evaluated are documented in [`docs/data/APIs_normalization.md`](./APIs_normalization.md) and are not duplicated here.


## Candidate Sources

Two sources remain under consideration as the primary data source for the MVP: Gupy and Meu Padrinho.

### Gupy

Gupy has a documented API and a consistent job listing structure. However, specific behaviors relevant to production use—such as pagination limits in practice, rate limits, and filter support—have not yet been fully validated against the live API and require further testing before a final decision can be made.

### Meu Padrinho

Testing against the live API revealed significant restrictions:

- The `page` parameter is 0-indexed. `page=0` returns HTTP 200 with 10 jobs; any `page >= 1` returns HTTP 204 (no content).
- The `offset`, `limit`, and `pagina` parameters are ignored.
- The only functional filter is niveis, which returns up to 10 jobs per level.
- Jobs are ordered from most recent to oldest.
- Out of approximately 27,600 total jobs, only a small, fixed subset (the most recent ones) is accessible through the API.

These constraints significantly limit both the volume and the time range of data that can be retrieved from Meu Padrinho as a standalone source.

## Alternatives Ruled Out

The following sources were evaluated and are not being considered as the primary MVP source (see `docs/data/APIs_normalization.md` for full technical details): **InHire**, **Solides**, **Trampos.co**, and **Quero Vagas Tech**.

## Proposed Polling / Scanning Approach

The following pipeline design is proposed for the selected source, pending approval together with the final source decision:

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
- Meu Padrinho's pagination limitation (described above) significantly restricts its usability as a complete standalone source for the MVP.
