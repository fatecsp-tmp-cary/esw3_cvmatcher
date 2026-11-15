# MVP Source Selection — Job Postings

## Status
APiBR is the single primary data source for the MVP. Source selection,
alternatives, polling approach, and limitations are defined below.

## Selected Source: APiBR

APiBR (https://apibr.com) was selected as the single primary job data source for the MVP.

- Base URL: `https://apibr.com/vagas/api/v2`
- Endpoints: `GET /vagas/api/v2/authors`, `GET /vagas/api/v2/issues`, `GET /vagas/api/v2/labels`, `GET /vagas/api/v2/repositories`
- API spec: OpenAPI 3.0
- License: MIT
- Historical assessment version: 2.3.0 (2026-08-20); this is not a current-version guarantee.

### Confirmed request parameters
- `per_page`: max 100 results per request
- `term`: keyword search (matches job title and description)
- `includeBody`: includes full job description in the response
- `page`: doesn't seem to have a page limit
- Additional queryable resources: `authors`, `labels`, `organizations`
- No seniority-level filter available

## Rejected Alternatives

### Gupy
Rejected as the primary source because endpoint availability is uncertain.
The access error's cause and status code are unconfirmed; anomalous traffic
detection must not be treated as established fact.

### Meu Padrinho
Considered due to a higher reported job volume (~27,600 total postings), but rejected due to:
- Broken pagination behavior: `page=0` returns HTTP 200 with 10 jobs; `page >= 1` returns HTTP 204; `offset`, `limit`, and `pagina` parameters are ignored
- Only the `niveis` filter is functional, limited to 10 jobs per level, restricting access to a small, fixed recent subset of the total volume
- Risk of data inconsistency under combined filters: a theoretical combination of filters was estimated to yield up to ~32,000 records (assuming disjoint categories), against a real benchmark of ~2,700, indicating unreliable or overlapping data
- Risk of future endpoint instability analogous to the one observed with Gupy

Only APiBR is selected for the initial integration. Additional adapters may be selected later.

### Other sources ruled out
InHire, Solides, Trampos.co, and Quero Vagas Tech were also evaluated and are not being considered for the MVP.

## Polling / Scanning Approach

1. Sequential requests to APiBR using `per_page=100`, incrementing `page` after each request, until an empty page is returned
2. For each job, apply `includeBody` to retrieve the full job description when needed.
3. `term` filtering is incremental-only; global health/count snapshot attestation uses the unfiltered issues-with-body dataset.
4. Normalize the data according to the shared schema.
5. Upsert each job record using its surrogate primary key and enforce unique source identity with `(platform, source_job_id)`. Reject source records with missing or blank identifiers; identifiers from different platforms remain independent.
6. Jobs absent from a successful complete snapshot may be marked `STALE`; the
   APiBR scan must qualify under accepted ADR-013 before relying on coverage.
   The separate absence/stale-expiration policy remains #145 and is not enabled
   by attestation alone.

This approach avoids relying on real-time webhooks and keeps the dataset up to date through scheduled polling.

## Limitations and Restrictions
- No seniority filter is available on APiBR; seniority must be inferred downstream if needed.
- Job body format is not standardized across sources aggregated by APiBR.
- Coverage depends entirely on the repositories/accounts currently aggregated by APiBR.
- Authentication requirements, if any, have not been independently confirmed.
- Candidate profiles, candidate embeddings, and match results are request-scoped and never persisted or logged.
- Jobs from different sources are not merged or deduplicated.
- Location and work arrangement are not used for geographic eligibility filtering.
- All requests respect the source's rate limits, terms of use, and access restrictions, per `CONTRIBUTING.md`.


## Implementation clarification status

The scan proposal alone does not establish completeness. Accepted
[ADR-013](../architecture/decisions/ADR-013-best-effort-apibr-snapshot-attestation.md)
adds explicit SNAPSHOT health/count attestation, with documented concurrent-rewrite
limitations. Absence-driven transitions remain separate #145 work. The source identity
decision is settled: enforce unique `(platform, source_job_id)` and reject
missing or blank source identifiers. See the
[MVP acceptance clarifications](../../specs/feature-001-mvp/acceptance.md).
APiBR aggregates GitHub issues: `state=open` normalizes to `ACTIVE`, and
`state=closed` normalizes to `EXPIRED`.
Missing state leaves new jobs `DISCOVERED`; ingestion performs no GitHub
availability requests. Existing availability and verification timestamps are
retained when evidence is absent. Malformed records are rejected individually
and valid records commit as `PARTIAL`; network/pagination failure rolls back
job changes and records `FAILED`. Fetch and normalize all pages and finish remote
snapshot attestation before locking job identities. Acquire at most 256 PostgreSQL
advisory stripes in ascending order, then apply buffered observations in original
order within the outer transaction. This avoids remote waits under identity locks
and opposite-order batch deadlocks; stripe collisions only serialize unrelated
records. Final persistence rejections also invalidate snapshot qualification.
Incremental and nonqualifying scans remain incomplete; even qualifying scans do
not invent job availability. See
[ADR-003](../architecture/decisions/ADR-003-apibr-availability-and-partial-runs.md).

The captured fixture is a GitHub issue, not a confirmed APiBR
response. A separate synthetic state-free fixture prevents hidden network
access in tests. Live response shape, rate limits, authentication and retention rights remain
unverified source-evidence follow-ups, including #113.

## Current bounded count observation (2026-11-12)

The [aggregate count probe](../reports/2026-11-12-apibr-count-attestation.json)
observed 728 distinct IDs, an empty terminal page, zero duplicates/rejections and
unchanged healthy body-dataset count/update signatures before/after pagination.
No raw responses, poster details or source text were retained. All records lacked
explicit state and therefore remain DISCOVERED. The user adopted the stricter
best-effort exact-count rule in ADR-013; this is not an immutable snapshot proof
or evidence of source usage/retention rights. Operator configuration, bounded
requests and invalid/partial scan protection are in the
[source-adapter policy](source-adapters.md).
