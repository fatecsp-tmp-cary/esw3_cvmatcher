# MVP Source Selection — Job Postings

## Status
This document reflects the final decision for the MVP job ingestion pipeline. APiBR was defined as the single primary data source for the MVP, as decided by the Data Squad and communicated to the team on 2026-10-07. This decision follows the access issue observed with Gupy during the team meeting on 2026-10-06 and the risk assessment performed for Meu Padrinho. The Definition of Done for this task (selected source, rejected alternatives, polling approach, and limitations) is addressed in full below.

## Selected Source: APiBR

APiBR (https://apibr.com) was selected as the single primary job data source for the MVP.

- Base URL: `https://apibr.com/vagas/api/v2`
- Endpoints: `GET /vagas/api/v2/authors`, `GET /vagas/api/v2/issues`, `GET /vagas/api/v2/labels`, `GET /vagas/api/v2/repositories`
- API spec: OpenAPI 3.0
- License: MIT
- Production version: 2.3.0 (last updated 2026-08-20)

### Confirmed request parameters
- `per_page`: max 100 results per request
- `term`: keyword search (matches job title and description)
- `includeBody`: includes full job description in the response
- `page`: tested from 1 to 31; page 32 and beyond return no results
- Additional queryable resources: `authors`, `labels`, `organizations`
- No seniority-level filter available

## Rejected Alternatives

### Gupy
Previously considered as the primary source. During the team meeting on 2026-10-06, multiple team members encountered an HTTP error when attempting to access the Gupy endpoint. The exact cause and status code could not be confirmed. It was hypothesized that this could be related to anomalous traffic detection on Gupy's side, but this has not been confirmed and should not be treated as established fact. Given the uncertainty around endpoint availability and the risk of losing access after implementation, Gupy was ruled out as the primary source.

### Meu Padrinho
Considered due to a higher reported job volume (~27,600 total postings), but rejected due to:
- Broken pagination behavior: `page=0` returns HTTP 200 with 10 jobs; `page >= 1` returns HTTP 204; `offset`, `limit`, and `pagina` parameters are ignored
- Only the `niveis` filter is functional, limited to 10 jobs per level, restricting access to a small, fixed recent subset of the total volume
- Risk of data inconsistency under combined filters: a theoretical combination of filters was estimated to yield up to ~32,000 records (assuming disjoint categories), against a real benchmark of ~2,700, indicating unreliable or overlapping data
- Risk of future endpoint instability analogous to the one observed with Gupy

Per project manager's request, the MVP uses a single primary source rather than combining primary and complementary sources. For this reason, Meu Padrinho is not used in the pipeline, despite its higher reported volume.

### Other sources ruled out
InHire, Solides, Trampos.co, and Quero Vagas Tech were also evaluated and are not being considered for the MVP.

## Polling / Scanning Approach

1. Sequential requests to APiBR using `per_page=100`, incrementing `page` after each request, until an empty page is returned (observed to occur at page 32).
2. For each job, apply `includeBody` to retrieve the full job description when needed.
3. Use `term` for keyword-based filtering when applicable.
4. Normalize the data according to the shared schema.
5. Upsert each job record using a surrogate primary key; `source_job_id` is stored as an attribute, not as the primary key, since identifiers may collide across sources.
6. Jobs no longer present in a subsequent scan are marked as INACTIVE.

This approach avoids relying on real-time webhooks and keeps the dataset up to date through scheduled polling.

## Limitations and Restrictions
- No seniority filter is available on APiBR; seniority must be inferred downstream if needed.
- Job body format is not standardized across sources aggregated by APiBR.
- Coverage depends entirely on the repositories/accounts currently aggregated by APiBR.
- Authentication requirements, if any, have not been independently confirmed.
- No candidate profile data or match results are persisted or logged, per `PLAN.md`.
- No deduplication of jobs across multiple sources is performed, per `PLAN.md`.
- No geographic eligibility filtering is applied, per `PLAN.md`.
- All requests respect the source's rate limits, terms of use, and access restrictions, per `CONTRIBUTING.md`.
