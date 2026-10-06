MVP Source Selection
Status
This document reflects the final decision for the MVP job ingestion pipeline. Following validation documented in docs/data/APIs_normalization.md (PR #71), Gupy has been confirmed as the primary data source for the MVP, as approved by the project manager. The Definition of Done for this task (selected source, rejected alternatives, polling approach, and limitations) is addressed in full below.

Full endpoint specifications, request/response schemas, and the technical comparison matrix for all sources evaluated are documented in docs/data/APIs_normalization.md and are not duplicated here.

Selected Source
Gupy (Primary)
Gupy was selected as the primary source for the MVP. Its pagination mechanism uses offset + limit, allowing sequential collection of a larger set of job postings. No major limitation was identified during testing.

Main Endpoint: GET https://employability-portal.gupy.io/api/v1/jobs
Format / Authentication: JSON responses, no authentication required.
Available Parameters: jobName (keyword search), limit (max. 100), offset.
Returned Fields: id, name (title), careerPageName (company), description, city, state, country, workplaceType, publishedDate, jobUrl.
Complementary Source
Meu Padrinho
Meu Padrinho was initially considered as a candidate for the primary source, but testing against the live API revealed significant restrictions:

The page parameter is 0-indexed. page=0 returns HTTP 200 with 10 jobs; any page >= 1 returns HTTP 204 (no content).
The offset, limit, and pagina parameters are ignored.
The only functional filter is niveis, which returns up to 10 jobs per level.
Jobs are ordered from most recent to oldest.
Out of approximately 27,600 total jobs, only a small, fixed subset (the most recent ones) is accessible through the API.
These constraints significantly limit both the volume and the time range of data that can be retrieved from Meu Padrinho as a standalone source. For this reason, Meu Padrinho was not selected as the primary source and remains a complementary source, used to collect additional recent jobs via the niveis filter.

Alternatives Ruled Out
The following sources were evaluated and are not being considered for the primary MVP role (see docs/data/APIs_normalization.md for full technical details): InHire, Solides, Trampos.co, Quero Vagas Tech, and APiBR (GitHub Vagas aggregator).

Polling / Scanning Approach
The following pipeline design is adopted for the selected sources:

Primary source (Gupy): sequential requests using limit=100, incrementing offset after each request until an empty result set is returned.
Complementary source (Meu Padrinho): requests using page=0 combined with the available niveis filters. Requests with page >= 1 are avoided, since they return HTTP 204.
For each job, fetch detail/skills information as needed.
Normalize the data according to the shared schema.
Upsert each job record using its unique job identifier.
Jobs no longer present in a subsequent scan are marked as INACTIVE.
This approach avoids relying on real-time webhooks and keeps the dataset up to date through scheduled polling.

Limitations and Restrictions
No candidate profile data or match results are persisted or logged, per PLAN.md.
No deduplication of jobs across multiple sources is performed, per PLAN.md.
No geographic eligibility filtering is applied, per PLAN.md.
All requests respect the source's rate limits, terms of use, and access restrictions, per CONTRIBUTING.md.
Meu Padrinho's pagination limitation (described above) significantly restricts its usability as a complete standalone source; it is used only as a complementary source for recent jobs.
