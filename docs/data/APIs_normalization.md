# API, Endpoint, and Job Normalization Documentation (MVP)

This document records endpoint research for evaluated sources. APiBR is selected for the initial integration; the remaining sources are candidates, not selected integrations.

## 1. Canonical Schema

Since each job API returns different JSON structures, all data collected by the integrators is transformed and mapped to the following standardized schema before being persisted:

| Normalized Field | Data Type | Description / Transformation Rule | Example Value |
|---|---|---|---|
| `id` | Internal identifier | Stable identifier assigned by CV-Match. | `0012345` |
| `source_job_id` | String | Unique identifier originally provided by the platform | `"MOaYsJOw"` or `"12577603"` |
| `platform` | String | Name of the platform/API from which the data was collected | `"apibr"` |
| `source_expires_at` | Timestamp or null | Explicit expiration supplied by the source. Missing value does not mean expired. | `"2026-12-31T23:59:59Z"` |
| `title` | String | Cleaned and formatted job title | `"Mid-Level Data Analyst"` |
| `company` | String | Name of the hiring company or career page | `"Globo"`, `"Archer Daniels"` |
| `description` | Text | Full descriptive text or job requirements | `"Responsible for data modeling..."` |
| `keywords` | Array[String] | List of keywords related to the job, such as skill, location and seniority requirements | `{"Python", "Pleno", "Django", "Remoto"}` |
| `location` | JSON / Obj | Standardized object containing city, state, and country | `{"city": "SP", "state": "SP"}` |
| `work_arrangement` | Enum | Work arrangement (REMOTE, HYBRID, ON_SITE) | `HYBRID` |
| `seniority_level` | Enum | Seniority level (INTERN, JUNIOR, MID, SENIOR, SPECIALIST, COORDINATOR) | `MID` |
| `skills` | Array[String] | List of skills, programming languages, frameworks, tools, or other relevant requirements | `["Python", "SQL", "Docker"]` |
| `salary` | JSON / Obj | Salary range when available | `{"min": 5000, "max": 7000}` |
| `currency` | String | Currency associated with salary, when supplied. | `"BRL"` |
| `job_url` | String | Direct link to the job opening in that specific platform | `"https://example.com/jobs/12577603"` |
| `publication_date` | Timestamp | Publication date/time standardized in ISO 8601 format | `"2026-09-23T07:04:10Z"` |
| `status` | Enum | `DISCOVERED`, `ACTIVE`, `STALE`, or `EXPIRED`; availability follows the lifecycle rules below. | `"ACTIVE"` |
| `first_seen_at` | Timestamp | First successful observation by the collector. | `"2026-10-20T12:05:00Z"` |
| `last_seen_at` | Timestamp | Most recent successful observation. | `"2026-10-20T12:05:00Z"` |
| `last_verified_at` | Timestamp or null | Most recent successful availability check. | `"2026-10-20T12:05:00Z"` |
| `raw` | JSON | Original source payload, only when retention is permitted. | `{ "id": 12577603 }` |
| `embedding` | pgvector value | Job embedding; null means missing or invalid for the configured model. | `vector([...])` |
| `content_hash` | String | Hash of normalized job content, used to detect changes. | `"sha256:…"` |

`skills` and structured requirements may also use the supporting `skills`, `job_skills`, and `job_requirements` tables. Candidate profiles, candidate embeddings, and match results are request-scoped and are not part of this persisted schema.

## 2. Technical Specification and Endpoints for All Sources

### 2.1 Meu Padrinho / API Vagas Tech (Evaluated; not selected for initial integration)

Main Endpoint: GET [https://meupadrinho.com.br/api/vagas](https://meupadrinho.com.br/api/vagas)

Details Endpoint: GET `https://meupadrinho.com.br/api/vagas/{nano_id}`

Technologies Endpoint: GET `https://meupadrinho.com.br/api/vagas/{nano_id}/tecnologias`

| Parameter / Attribute | Technical Detail / Value |
|---|---|
| Method / Format / Authentication | GET / JSON / No authentication identified |
| Parameters | page (pagination), niveis (estagio, junior, pleno, senior) |
| Identifier / Title / Company | nano_id (or id) |
| Work Arrangement / Registration Date | forma_trabalho |
| Pagination Behavior | page is zero-indexed. page=0 returns approximately 10 jobs, while page>=1 returned HTTP 204 No Content during testing. |
| Additional Endpoint Mapping | Requires calls to /api/vagas/{nano_id} (for description, salary, and location) and /tecnologias (for the skills array). |
| Additional Collection Behavior | offset, limit, and pagina were ignored during testing. The niveis parameter can expose additional jobs by seniority level. |
| Main Limitation | Only a small subset of the available jobs can be collected. Approximately 27,600 jobs were observed in the source, but pagination does not provide access to the complete dataset. |

### 2.2 InHire (Public Tenant-Based Portal)

Main Endpoint: GET [https://api.inhire.app/job-posts/public/pages](https://api.inhire.app/job-posts/public/pages)

Required Header: `X-Tenant: <company_name>` (e.g., `X-Tenant: magalu`)

| Parameter / Attribute | Technical Detail / Value |
|---|---|
| Method / Format / Authentication | GET |
| Returned Fields | jobId, displayName (title), tenantName (company), workplaceType, location |
| Behavior / Limitation | Does not have pagination or global keyword search. Returns all active jobs associated with the specified X-Tenant. Prior knowledge of the companies is required. |

### 2.3 Solides

Main Endpoint: GET [https://apigw.solides.com.br/jobs/v3/portal-vacancies](https://apigw.solides.com.br/jobs/v3/portal-vacancies)

Example Request: GET [https://apigw.solides.com.br/jobs/v3/portal-vacancies?title=Analista%20de%20Dados&page=1&take=25](https://apigw.solides.com.br/jobs/v3/portal-vacancies?title=Analista%20de%20Dados\&page=1\&take=25)

| Parameter / Attribute | Technical Detail / Value |
|---|---|
| Method / Format / Authentication | GET |
| Parameters | title (search term), page (page), take (limit per page, default 25) |
| Returned Fields | ID, title, company, description, location, work arrangement, publication date, direct link |
| Pagination Behavior | Uses page + take. Increments page while keeping take=25 until the end of the records. |

### 2.4 Trampos.co

Main Endpoint: GET [https://trampos.co/api/v2/opportunities](https://trampos.co/api/v2/opportunities)

Example Request: GET [https://trampos.co/api/v2/opportunities?tr=Analista%20de%20Dados&lc=Sao%20Paulo&page=1](https://trampos.co/api/v2/opportunities?tr=Analista%20de%20Dados\&lc=Sao%20Paulo\&page=1)

| Parameter / Attribute | Technical Detail / Value |
|---|---|
| Method / Format / Authentication | GET |
| Parameters | tr (search term), lc (location), page (page) |
| Returned Fields | ID, title, company, location, work arrangement, job link (description is partial) |
| Pagination Behavior | The response contains the pagination.total_pages key. The collector reads the total and schedules requests from page=1 through total_pages. |

### 2.5 Quero Vagas Tech

Main Endpoint: GET [https://querovagastech.com.br/api/jobs](https://querovagastech.com.br/api/jobs)

Details Endpoint: GET `https://querovagastech.com.br/api/jobs/{id}`

Example Request: GET [https://querovagastech.com.br/api/jobs?page=1&pageSize=100&sort=postedAt:desc](https://querovagastech.com.br/api/jobs?page=1\&pageSize=100\&sort=postedAt:desc)

| Parameter / Attribute | Technical Detail / Value |
|---|---|
| Method / Format / Authentication | GET |
| Parameters | page (page), pageSize (max. 100), sort (sorting, e.g., postedAt:desc) |
| Returned Fields | id, title, company, postedAt, work arrangement, location |
| Pagination Behavior | Uses page + pageSize. To obtain the complete description and additional data, a secondary call to /api/jobs/{id} is performed. |

### 2.6 APiBR / Vagas Aggregator (Selected initial source)

**Official API Documentation (Swagger):** [https://apibr.com/vagas/swagger/](https://apibr.com/vagas/swagger/)

Main Endpoint: GET [https://apibr.com/vagas/api/v2/issues](https://apibr.com/vagas/api/v2/issues)

Authors Endpoint: GET `/vagas/authors`

Labels Endpoint: GET `/vagas/labels`

Repositories Endpoint: GET `/vagas/repositories`

| Parameter / Attribute | Technical Detail / Value |
|---|---|
| Method / Format / Authentication | GET / JSON / No authentication identified |
| Main Resource | Job opportunities represented as GitHub issues |
| Additional Resources | Authors, labels, and repositories |
| Pagination Behavior | The page parameter was tested and returned different sets of jobs for different page values. Pages from 1 through 31 returned results during testing; from page=32 onward, no results were returned. |
| Limit Parameter | The limit parameter was tested with different values but did not change the number of results returned. |
| Keyword Search | Not identified as a confirmed query parameter in the available API documentation. |
| Returned Data | Job information associated with GitHub issues and source metadata, including issue ID, title, URL, keywords, labels, author, comments, and repository information. |
| Labels / Metadata | Labels can provide information such as technologies (Kubernetes, Terraform, Docker), seniority (Pleno), work arrangement (Híbrido), employment type (CLT, PJ), location/scope (Brasil, Nacional), and salary range (R$ 8k - 12k). |
| Main Limitation | The endpoint has a limited observed pagination range of 31 pages, and the number of results per page cannot be controlled through the tested limit parameter. Coverage also depends on the repositories and accounts included in the aggregator. |

## 3. 📊 Summary Comparison Matrix

| Criterion / API | APiBR | Meu Padrinho | InHire | Solides | Trampos.co | Quero Vagas Tech |
|---|---|---|---|---|---|---|
| Selection status | Selected initial source | Evaluated, not selected | Evaluated, not selected | Evaluated, not selected | Evaluated, not selected | Evaluated, not selected |
| HTTP Method | GET | GET | GET | GET | GET | GET |
| JSON Response | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Authentication Required | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No | ❌ No |
| Limit per Request | Not identified / limit ignored | ~10 observed | N/A | 25 (take) | Not identified | 100 |
| Pagination Mechanism | page (tested up to page=31) | page (not functional beyond page=0) | N/A | page | page | page |
| Keyword Search | Not identified | ❌ | ❌ | ✅ title | ✅ tr | ❌ |
| Seniority Filter | Not identified | ✅ niveis | ❌ | ❌ | ❌ | ❌ |
| Description Included | Not confirmed | Additional endpoint | ❌ | ✅ | Partial | Additional endpoint |
| Unique Identifier | Issue ID (id) | nano_id | jobId | ID | ID | id |
| Main Limitation | Pagination observed up to 31 pages; limit ignored; coverage depends on aggregated repositories | Pagination unavailable; only a small recent subset is accessible | Requires Tenant | take=25 limit | Partial description | No text search |

## 4. ⚙️ Data Collection and Data Engineering Pipeline

**List Ingestion (APiBR):** The collector makes sequential requests to the primary source (APiBR), using the `page` parameter starting at page=1 and incrementing it until no more results are returned. During testing, pages 1 through 31 returned results, while page=32 onward returned no results.

**Other-source evaluation:** Meu Padrinho was evaluated using page=0 and `niveis`; page>=1 returned HTTP 204 during testing. It is not part of the selected initial integration.

**Evaluated details and skills collection:** During Meu Padrinho testing, the `nano_id` was used to request `/api/vagas/{nano_id}` (description, location, salary) and `/api/vagas/{nano_id}/tecnologias`.

**Data Normalization:** All returned attributes are converted to the Normalized Schema defined in Section 1.

**Incremental Deduplication (Upsert):**

The system checks the `source_job_id` together with the `platform` in the database.

If the job already exists, the job data is updated.

If it is new, the record is inserted.

Only successful complete snapshots may mark absent jobs `STALE`; failed polls and incremental absence leave lifecycle state unchanged.



## 5. MVP Source Selection

### 5.1 APiBR as the Official Primary Source

**APiBR was selected as the primary source for the MVP.**

Official API documentation: [https://apibr.com/vagas/swagger/](https://apibr.com/vagas/swagger/)

APiBR was selected because it provides publicly accessible job data in JSON format without authentication during testing. Its vacancies are represented as GitHub issues, with metadata such as issue IDs, titles, URLs, timestamps, keywords, labels, authors, comments, and repository information.

Live testing showed the following pagination behavior:

- The `limit` parameter did not change the number of results returned.
- No confirmed keyword-search parameter was identified.

This was selected as the official primary source for the MVP since its structured issue metadata and labels can support the normalization process and CV-to-job matching.

### 5.2 Other Evaluated Sources

**Meu Padrinho / API Vagas Tech** was initially considered as the main source because it provides structured job data and additional endpoints for job details and technologies. However, live testing showed that its pagination is not functional:

- page=0 returns approximately 10 jobs.
- page>=1 returns HTTP 204 No Content.
- offset, limit, and pagina were ignored during testing.
- The niveis parameter can expose additional jobs by seniority.
- Only a small fraction of the available job universe can therefore be collected.

For this reason, Meu Padrinho was not selected for the initial integration; it remains an evaluated candidate.

**InHire** may be considered in the future when the project has a defined list of companies whose vacancies should be collected.

**Solides, Trampos.co, and Quero Vagas Tech** remain evaluated candidates for possible future selection.

### 5.3 Gupy Exclusion

Gupy was removed from the MVP source selection because its API became unavailable during the project's evaluation and will no longer be used.

### 5.4 Selection Summary

The initial integration will use APiBR. The other evaluated APIs are candidates for future selection, not selected integrations.

This approach selects APiBR for the initial integration while preserving the evaluation needed to consider other sources later.
