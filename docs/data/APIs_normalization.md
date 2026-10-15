# API, Endpoint, and Job Normalization Documentation (MVP)

This document specifies the data architecture, endpoint mapping for all 6 evaluated public sources retained in the project, the definition of the platform selected for the MVP, and the normalization and standardization schema for the unified database.

## 1. Schema Normalization Strategy (Unified Model)

Since each job API returns different JSON structures, all data collected by the integrators is transformed and mapped to the following standardized schema before being persisted:

| Normalized Field | Data Type | Description / Transformation Rule | Example Value |
|---|---|---|---|
| `source_job_id` | String (PK) | Unique identifier originally provided by the platform | `"MOaYsJOw"` or `"12577603"` |
| `platform` | String | Name of the platform/API from which the data was collected | `"Meu Padrinho"`, `"APiBR"` |
| `title` | String | Cleaned and formatted job title | `"Mid-Level Data Analyst"` |
| `company` | String | Name of the hiring company or career page | `"Globo"`, `"Archer Daniels"` |
| `description` | Text | Full descriptive text or job requirements | `"Responsible for data modeling..."` |
| `location` | JSON / Obj | Standardized object containing city, state, and country | `{"city": "SP", "state": "SP"}` |
| `work_arrangement` | Enum | Work arrangement (REMOTE, HYBRID, ON_SITE) | `HYBRID` |
| `seniority_level` | Enum | Seniority level (INTERN, JUNIOR, MID, SENIOR, SPECIALIST, COORDINATOR) | `MID` |
| `skills` | Array[String] | List of skills, programming languages, frameworks, tools, or other relevant requirements | `["Python", "SQL", "Docker"]` |
| `salary` | JSON / Obj | Salary range when available | `{"min": 5000, "max": 7000}` |
| `job_url` | String | Direct link to the job opening in that specific platform | `"https://..."` |
| `publication_date` | Timestamp | Publication date/time standardized in ISO 8601 format | `"2026-09-23T07:04:10Z"` |
| `source_status` | Enum | Job status reported by the source/platform (ACTIVE, INACTIVE, UNAVAILABLE) | `ACTIVE` |

## 2. Technical Specification and Endpoints for All Sources

### 2.1 Meu Padrinho / API Vagas Tech (Complementary Source)

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

### 2.6 APiBR / Vagas Aggregator (MVP Main Source)

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
| MVP Role | Main Source | Complementary | Potential | Potential | Potential | Potential |
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

**Complementary Source Collection:** The collector may query Meu Padrinho using page=0 and the available niveis filters to collect additional recent jobs. Requests to page>=1 should not be used because pagination was found to return HTTP 204 No Content during testing. Other evaluated sources may be integrated in future iterations, depending on project priorities and further API testing.

**Details and Skills Collection:** For each Meu Padrinho job, the system extracts the nano_id and makes parallel requests to `/api/vagas/{nano_id}` (description, location, salary) and `/api/vagas/{nano_id}/tecnologias`.

**Data Normalization:** All returned attributes are converted to the Normalized Schema defined in Section 1.

**Incremental Deduplication (Upsert):**

The system checks the source_job_id together with the platform in the database.

If the job already exists, the job data is updated.

If it is new, the record is inserted.

**Source Status:** The source_status field represents the status provided by the source/platform (ACTIVE, INACTIVE, UNAVAILABLE).

## 5. MVP Source Selection

### 5.1 APiBR as the Official Primary Source

**APiBR was selected as the primary source for the MVP.**

Official API documentation: [https://apibr.com/vagas/swagger/](https://apibr.com/vagas/swagger/)

APiBR was selected because it provides publicly accessible job data in JSON format without authentication during testing. Its vacancies are represented as GitHub issues, with metadata such as issue IDs, titles, URLs, timestamps, keywords, labels, authors, comments, and repository information.

Live testing showed the following pagination behavior:

- Pages 1 through 31 returned results.
- Page 32 onward returned no results.
- The `limit` parameter did not change the number of results returned.
- No confirmed keyword-search parameter was identified.

Although the API has pagination and coverage limitations, it was selected as the official primary source for the MVP. Its structured issue metadata and labels can support the normalization process and CV-to-job matching.

### 5.2 Complementary and Alternative Sources

**Meu Padrinho / API Vagas Tech** was initially considered as the main source because it provides structured job data and additional endpoints for job details and technologies. However, live testing showed that its pagination is not functional:

- page=0 returns approximately 10 jobs.
- page>=1 returns HTTP 204 No Content.
- offset, limit, and pagina were ignored during testing.
- The niveis parameter can expose additional jobs by seniority.
- Only a small fraction of the available job universe can therefore be collected.

For this reason, Meu Padrinho will be kept as a complementary source, mainly for collecting additional recent jobs through the available filters.

**InHire** may be considered in the future when the project has a defined list of companies whose vacancies should be collected.

**Solides, Trampos.co, and Quero Vagas Tech** remain documented as potential complementary sources for future iterations of the project.

### 5.3 Gupy Exclusion

Gupy was removed from the MVP source selection because its API became unavailable during the project's evaluation and will no longer be used.

### 5.4 Selection Summary

The MVP will prioritize APiBR as its official primary source. The other evaluated APIs retained in this document remain potential complementary sources to expand vacancy coverage in future development cycles.

This approach establishes a single primary source for the initial integration while preserving the technical evaluation needed to add other sources later.
