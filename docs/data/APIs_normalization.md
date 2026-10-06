# API, Endpoint, and Job Normalization Documentation (MVP)

This document specifies the data architecture, endpoint mapping for all 7 evaluated public sources, the definitions of the platform selected for the MVP, and the **normalization and standardization schema** for the unified database.

---

## 1. Schema Normalization Strategy (Unified Model)

Since each job API returns different JSON structures, all data collected by the integrators is transformed and mapped to the following standardized schema before being persisted:

| **Normalized Field** | **Data Type**   | **Description / Transformation Rule**                                                    | **Example Value**                    |
| -------------------- | --------------- | ---------------------------------------------------------------------------------------- | ------------------------------------ |
| `source_job_id`      | `String` (PK)   | Unique identifier originally provided by the platform                                    | `"MOaYsJOw"` or `"12577603"`         |
| `platform`           | `String`        | Name of the platform/API from which the data was collected                               | `"Meu Padrinho"`, `"Gupy"`           |
| `title`              | `String`        | Cleaned and formatted job title                                                          | `"Mid-Level Data Analyst"`           |
| `company`            | `String`        | Name of the hiring company or career page                                                | `"Globo"`, `"Archer Daniels"`        |
| `description`        | `Text`          | Full descriptive text or job requirements                                                | `"Responsible for data modeling..."` |
| `location`           | `JSON / Obj`    | Standardized object containing `city`, `state`, and `country`                            | `{"city": "SP", "state": "SP"}`      |
| `work_arrangement`   | `Enum`          | Work arrangement (`REMOTE`, `HYBRID`, `ON_SITE`)                                         | `HYBRID`                             |
| `seniority_level`    | `Enum`          | Seniority level (`INTERN`, `JUNIOR`, `MID`, `SENIOR`, `SPECIALIST`, `COORDINATOR`)       | `MID`                                |
| `skills`             | `Array[String]` | List of skills, programming languages, frameworks, tools, or other relevant requirements | `["Python", "SQL", "Docker"]`        |
| `salary`             | `JSON / Obj`    | Salary range when available                                                              | `{"min": 5000, "max": 7000}`         |
| `job_url`            | `String`        | Direct link to the job opening in that specific platform                                 | `"https://..."`                      |
| `publication_date`   | `Timestamp`     | Publication date/time standardized in ISO 8601 format                                    | `"2026-09-23T07:04:10Z"`             |
| `source_status`      | `Enum`          | Job status reported by the source/platform (`ACTIVE`, `INACTIVE`, `UNAVAILABLE`)         | `ACTIVE`                             |

---

## 2. Technical Specification and Endpoints for All Sources

### 2.1 Gupy (MVP Main Source)

* **Main Endpoint:** `GET https://employability-portal.gupy.io/api/v1/jobs`
* **Example Request:** `GET https://employability-portal.gupy.io/api/v1/jobs?jobName=Analista%20de%20Dados&limit=100&offset=0`

| **Parameter / Attribute**            | **Technical Detail / Value**                                                                                                                   |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication** | `GET` / JSON / No authentication identified                                                                                                    |
| **Parameters**                       | `jobName` (keyword search), `limit` (max. 100), `offset` (offset)                                                                              |
| **Returned Fields**                  | `id`, `name` (title), `careerPageName` (company), `description` (full), `city`, `state`, `country`, `workplaceType`, `publishedDate`, `jobUrl` |
| **Pagination Behavior**              | Uses `offset` + `limit`. The collector increases the `offset` until `results: []` is received.                                                 |

---

### 2.2 Meu Padrinho / API Vagas Tech (Complementary Source)

* **Main Endpoint:** `GET https://meupadrinho.com.br/api/vagas`
* **Details Endpoint:** `GET https://meupadrinho.com.br/api/vagas/{nano_id}`
* **Technologies Endpoint:** `GET https://meupadrinho.com.br/api/vagas/{nano_id}/tecnologias`

| **Parameter / Attribute**                | **Technical Detail / Value**                                                                                                                                                       |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication**     | `GET` / JSON / No authentication identified                                                                                                                                        |
| **Parameters**                           | `page` (pagination), `niveis` (`estagio`, `junior`, `pleno`, `senior`)                                                                                                             |
| **Identifier / Title / Company**         | `nano_id` (or `id`)                                                                                                                                                                |
| **Work Arrangement / Registration Date** | `forma_trabalho`                                                                                                                                                                   |
| **Pagination Behavior**                  | `page` is zero-indexed. `page=0` returns approximately 10 jobs, while `page>=1` returned HTTP `204 No Content` during testing.                                                     |
| **Additional Endpoint Mapping**          | Requires calls to `/api/vagas/{nano_id}` (for `description`, `salary`, and `location`) and `/tecnologias` (for the `skills` array).                                                |
| **Additional Collection Behavior**       | `offset`, `limit`, and `pagina` were ignored during testing. The `niveis` parameter can expose additional jobs by seniority level.                                                 |
| **Main Limitation**                      | Only a small subset of the available jobs can be collected. Approximately 27,600 jobs were observed in the source, but pagination does not provide access to the complete dataset. |

---

### 2.3 InHire (Public Tenant-Based Portal)

* **Main Endpoint:** `GET https://api.inhire.app/job-posts/public/pages`
* **Required Header:** `X-Tenant: <company_name>` (e.g., `X-Tenant: magalu`)

| **Parameter / Attribute**            | **Technical Detail / Value**                                                                                                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Method / Format / Authentication** | `GET`                                                                                                                                                              |
| **Returned Fields**                  | `jobId`, `displayName` (title), `tenantName` (company), `workplaceType`, `location`                                                                                |
| **Behavior / Limitation**            | Does not have pagination or global keyword search. Returns all active jobs associated with the specified `X-Tenant`. Prior knowledge of the companies is required. |

---

### 2.4 Solides

* **Main Endpoint:** `GET https://apigw.solides.com.br/jobs/v3/portal-vacancies`
* **Example Request:** `GET https://apigw.solides.com.br/jobs/v3/portal-vacancies?title=Analista%20de%20Dados&page=1&take=25`

| **Parameter / Attribute**            | **Technical Detail / Value**                                                                  |
| ------------------------------------ | --------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication** | `GET`                                                                                         |
| **Parameters**                       | `title` (search term), `page` (page), `take` (limit per page, default `25`)                   |
| **Returned Fields**                  | ID, title, company, description, location, work arrangement, publication date, direct link    |
| **Pagination Behavior**              | Uses `page` + `take`. Increments `page` while keeping `take=25` until the end of the records. |

---

### 2.5 Trampos.co

* **Main Endpoint:** `GET https://trampos.co/api/v2/opportunities`
* **Example Request:** `GET https://trampos.co/api/v2/opportunities?tr=Analista%20de%20Dados&lc=Sao%20Paulo&page=1`

| **Parameter / Attribute**            | **Technical Detail / Value**                                                                                                                      |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication** | `GET`                                                                                                                                             |
| **Parameters**                       | `tr` (search term), `lc` (location), `page` (page)                                                                                                |
| **Returned Fields**                  | ID, title, company, location, work arrangement, job link (description is partial)                                                                 |
| **Pagination Behavior**              | The response contains the `pagination.total_pages` key. The collector reads the total and schedules requests from `page=1` through `total_pages`. |

---

### 2.6 Quero Vagas Tech

* **Main Endpoint:** `GET https://querovagastech.com.br/api/jobs`
* **Details Endpoint:** `GET https://querovagastech.com.br/api/jobs/{id}`
* **Example Request:** `GET https://querovagastech.com.br/api/jobs?page=1&pageSize=100&sort=postedAt:desc`

| **Parameter / Attribute**            | **Technical Detail / Value**                                                                                                         |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Method / Format / Authentication** | `GET`                                                                                                                                |
| **Parameters**                       | `page` (page), `pageSize` (max. 100), `sort` (sorting, e.g., `postedAt:desc`)                                                        |
| **Returned Fields**                  | `id`, title, company, `postedAt`, work arrangement, location                                                                         |
| **Pagination Behavior**              | Uses `page` + `pageSize`. To obtain the complete description and additional data, a secondary call to `/api/jobs/{id}` is performed. |

---

### 2.7 APiBR / Vagas Aggregator

* **Swagger Documentation:** `https://apibr.com/vagas/swagger/`
* **Main Endpoint:** `GET https://apibr.com/vagas/api/v2/issues`
* **Authors Endpoint:** `GET /vagas/authors`
* **Labels Endpoint:** `GET /vagas/labels`
* **Repositories Endpoint:** `GET /vagas/repositories`

| **Parameter / Attribute**            | **Technical Detail / Value**                                                                                                                                                                                                                          |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication** | `GET` / JSON / No authentication identified                                                                                                                                                                                                           |
| **Main Resource**                    | Job opportunities represented as GitHub issues                                                                                                                                                                                                        |
| **Additional Resources**             | Authors, labels, and repositories                                                                                                                                                                                                                     |
| **Pagination Behavior**              | The `page` parameter was tested and returned different sets of jobs for different page values. Pages from `1` through `31` returned results during testing; from `page=32` onward, no results were returned.                                          |
| **Limit Parameter**                  | The `limit` parameter was tested with different values but did not change the number of results returned.                                                                                                                                             |
| **Keyword Search**                   | Not identified as a confirmed query parameter in the available API documentation.                                                                                                                                                                     |
| **Returned Data**                    | Job information associated with GitHub issues and source metadata, including issue ID, title, URL, keywords, labels, author, comments, and repository information.                                                                                    |
| **Labels / Metadata**                | Labels can provide information such as technologies (`Kubernetes`, `Terraform`, `Docker`), seniority (`Pleno`), work arrangement (`Híbrido`), employment type (`CLT`, `PJ`), location/scope (`Brasil`, `Nacional`), and salary range (`R$ 8k - 12k`). |
| **Main Limitation**                  | The endpoint has a limited observed pagination range of 31 pages, and the number of results per page cannot be controlled through the tested `limit` parameter. Coverage also depends on the repositories and accounts included in the aggregator.    |

---

## 3. 📊 Summary Comparison Matrix

| **Criterion / API**         | **Meu Padrinho**                                                 | **Gupy**                       | **InHire**      | **Solides**     | **Trampos.co**      | **Quero Vagas Tech** | **APiBR**                                                                                        |
| --------------------------- | ---------------------------------------------------------------- | ------------------------------ | --------------- | --------------- | ------------------- | -------------------- | ------------------------------------------------------------------------------------------------ |
| **HTTP Method**             | `GET`                                                            | `GET`                          | `GET`           | `GET`           | `GET`               | `GET`                | `GET`                                                                                            |
| **JSON Response**           | ✅                                                                | ✅                              | ✅               | ✅               | ✅                   | ✅                    | ✅                                                                                                |
| **Authentication Required** | ❌ No                                                             | ❌ No                           | ❌ No            | ❌ No            | ❌ No                | ❌ No                 | ❌ No                                                                                             |
| **Limit per Request**       | ~10 observed                                                     | 100                            | N/A             | 25 (`take`)     | Not identified      | 100                  | Not identified / `limit` ignored                                                                 |
| **Pagination Mechanism**    | `page` (not functional beyond `page=0`)                          | `offset`                       | N/A             | `page`          | `page`              | `page`               | `page` (tested up to `page=31`)                                                                  |
| **Keyword Search**          | ❌                                                                | ✅ `jobName`                    | ❌               | ✅ `title`       | ✅ `tr`              | ❌                    | Not identified                                                                                   |
| **Seniority Filter**        | ✅ `niveis`                                                       | ❌                              | ❌               | ❌               | ❌                   | ❌                    | Not identified                                                                                   |
| **Description Included**    | Additional endpoint                                              | ✅                              | ❌               | ✅               | Partial             | Additional endpoint  | Not confirmed                                                                                    |
| **Unique Identifier**       | `nano_id`                                                        | `id`                           | `jobId`         | ID              | ID                  | `id`                 | Issue ID (`id`)                                                                                  |
| **Main Limitation**         | Pagination unavailable; only a small recent subset is accessible | No major limitation identified | Requires Tenant | `take=25` limit | Partial description | No text search       | Pagination observed up to 31 pages; `limit` ignored; coverage depends on aggregated repositories |

---

## 4. ⚙️ Data Collection and Data Engineering Pipeline

1. **List Ingestion:** The collector makes sequential requests to the primary source (**Gupy**), using `limit=100` and increasing the `offset` until no more results are returned.
2. **Complementary Source Collection:** The collector may query **Meu Padrinho** using `page=0` and the available `niveis` filters to collect additional recent jobs. Requests to `page>=1` should not be used because pagination was found to return HTTP `204 No Content` during testing.
3. **Details and Skills Collection:** For each Meu Padrinho job, the system extracts the `nano_id` and makes parallel requests to `/api/vagas/{nano_id}` (description, location, salary) and `/api/vagas/{nano_id}/tecnologias`.
4. **Data Normalization:** All returned attributes are converted to the **Normalized Schema** defined in Section 1.
5. **Incremental Deduplication (Upsert):**

   * The system checks the `source_job_id` together with the `platform` in the database.
   * If the job already exists, the job data is updated.
   * If it is new, the record is inserted.
6. **Source Status:** The `source_status` field represents the status provided by the source/platform (`ACTIVE`, `INACTIVE`, `UNAVAILABLE`).

---

## 5. MVP Source Selection

**Gupy was selected as the primary source for the MVP.**

Meu Padrinho / API Vagas Tech was initially considered as the main source because it provides structured job data and additional endpoints for job details and technologies. However, live testing showed that its pagination is not functional:

* `page=0` returns approximately 10 jobs.
* `page>=1` returns HTTP `204 No Content`.
* `offset`, `limit`, and `pagina` were ignored during testing.
* The `niveis` parameter can expose additional jobs by seniority.
* Only a small fraction of the available job universe can therefore be collected.

For this reason, **Meu Padrinho will be kept as a complementary source**, mainly for collecting additional recent jobs through the available filters.

**Gupy was selected as the primary source because its pagination uses `offset` + `limit`, allowing sequential collection of a larger set of vacancies.**

The other evaluated sources remain documented as potential complementary sources for future iterations of the project.
