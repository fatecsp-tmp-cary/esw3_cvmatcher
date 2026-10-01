# API, Endpoint, and Job Normalization Documentation (MVP)

This document specifies the data architecture, endpoint mapping for all 6 evaluated public sources, the definitions of the platform selected for the MVP, and the **normalization and standardization schema** for the unified database.

---

## 1. Schema Normalization Strategy (Unified Model)

Since each job API returns different JSON structures, all data collected by the integrators is transformed and mapped to the following standardized schema before being persisted:

| Normalized Field    | Data Type       | Description / Transformation Rule                             | Example Value                        |
| :------------------ | :-------------- | :------------------------------------------------------------ | :----------------------------------- |
| `id_vaga_origem`    | `String` (PK)   | Unique identifier originally provided by the platform         | `"MOaYsJOw"` or `"12577603"`         |
| `plataforma`        | `String`        | Name of the platform/API from which the data was collected    | `"Meu Padrinho"`, `"Gupy"`           |
| `titulo`            | `String`        | Cleaned and formatted job title                               | `"Mid-Level Data Analyst"`           |
| `empresa`           | `String`        | Name of the hiring company or career page                     | `"Globo"`, `"Archer Daniels"`        |
| `descricao`         | `Text`          | Full descriptive text or job requirements                     | `"Responsible for data modeling..."` |
| `localizacao`       | `JSON / Obj`    | Standardized object containing `city`, `state`, and `country` | `{"city": "SP", "state": "SP"}`      |
| `modalidade`        | `Enum`          | Work arrangement (`REMOTE`, `HYBRID`, `ON_SITE`)              | `HYBRID`                             |
| `nivel_senioridade` | `Enum`          | Seniority level (`INTERN`, `JUNIOR`, `MID`, `SENIOR`)         | `MID`                                |
| `tecnologias`       | `Array[String]` | List of programming languages, frameworks, and tools          | `["Python", "SQL", "Docker"]`        |
| `salario`           | `JSON / Obj`    | Salary range when available                                   | `{"min": 5000, "max": 7000}`         |
| `url_vaga`          | `String`        | Direct link to the application page                           | `"https://..."`                      |
| `data_publicacao`   | `Timestamp`     | Publication date/time standardized in ISO 8601 format         | `"2026-09-23T07:04:10Z"`             |
| `status`            | `Enum`          | Job status in our system (`ACTIVE`, `INACTIVE`)               | `ACTIVE`                             |

---

## 2. Technical Specification and Endpoints for All Sources

### 2.1 Meu Padrinho / API Vagas Tech (MVP Main Source)

* **Main Endpoint:** `GET https://meupadrinho.com.br/api/vagas`
* **Details Endpoint:** `GET https://meupadrinho.com.br/api/vagas/{nano_id}`
* **Technologies Endpoint:** `GET https://meupadrinho.com.br/api/vagas/{nano_id}/tecnologias`

| Parameter / Attribute                    | Technical Detail / Value                                                                                                            |
| :--------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication**     | `GET` | `JSON` | No authentication required                                                                                         |
| **Parameters**                           | `page` (pagination), `niveis` (`estagio`, `junior`, `pleno`, `senior`)                                                              |
| **Identifier / Title / Company**         | `nano_id` (or `id`) | `titulo_vaga` | `empresa_nome`                                                                                |
| **Work Arrangement / Registration Date** | `forma_trabalho` | `horario_registro`                                                                                               |
| **Pagination Behavior**                  | Uses `page`. Queries successive pages (`page=1`, `page=2`, ...) until an empty list `[]` or an error is returned.                   |
| **Additional Endpoint Mapping**          | Requires calls to `/api/vagas/{nano_id}` (for `description`, `salary`, and `location`) and `/tecnologias` (for the `skills` array). |

---

### 2.2 Gupy (Public Employability Portal)

* **Main Endpoint:** `GET https://employability-portal.gupy.io/api/v1/jobs`
* **Example Request:** `GET https://employability-portal.gupy.io/api/v1/jobs?jobName=Analista%20de%20Dados&limit=100&offset=0`

| Parameter / Attribute                | Technical Detail / Value                                                                                                                       |
| :----------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication** | `GET` | `JSON` | No authentication required                                                                                                    |
| **Parameters**                       | `jobName` (keyword search), `limit` (max. 100), `offset` (offset)                                                                              |
| **Returned Fields**                  | `id`, `name` (title), `careerPageName` (company), `description` (full), `city`, `state`, `country`, `workplaceType`, `publishedDate`, `jobUrl` |
| **Pagination Behavior**              | Uses `offset` + `limit`. Increases the `offset` by 100 until `results: []` is received.                                                        |

---

### 2.3 InHire (Public Tenant-Based Portal)

* **Main Endpoint:** `GET https://api.inhire.app/job-posts/public/pages`
* **Required Header:** `X-Tenant: <company_name>` (e.g., `X-Tenant: magalu`)

| Parameter / Attribute                | Technical Detail / Value                                                                                                                                           |
| :----------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication** | `GET` | `JSON` | No authentication required                                                                                                                        |
| **Returned Fields**                  | `jobId`, `displayName` (title), `tenantName` (company), `workplaceType`, `location`                                                                                |
| **Behavior / Limitation**            | Does not have pagination or global keyword search. Returns all active jobs associated with the specified `X-Tenant`. Prior knowledge of the companies is required. |

---

### 2.4 Solides

* **Main Endpoint:** `GET https://apigw.solides.com.br/jobs/v3/portal-vacancies`
* **Example Request:** `GET https://apigw.solides.com.br/jobs/v3/portal-vacancies?title=Analista%20de%20Dados&page=1&take=25`

| Parameter / Attribute                | Technical Detail / Value                                                                      |
| :----------------------------------- | :-------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication** | `GET` | `JSON` | No authentication required                                                   |
| **Parameters**                       | `title` (search term), `page` (page), `take` (limit per page, default `25`)                   |
| **Returned Fields**                  | ID, title, company, description, location, work arrangement, publication date, direct link    |
| **Pagination Behavior**              | Uses `page` + `take`. Increments `page` while keeping `take=25` until the end of the records. |

---

### 2.5 Trampos.co

* **Main Endpoint:** `GET https://trampos.co/api/v2/opportunities`
* **Example Request:** `GET https://trampos.co/api/v2/opportunities?tr=Analista%20de%20Dados&lc=Sao%20Paulo&page=1`

| Parameter / Attribute                | Technical Detail / Value                                                                                                                          |
| :----------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Method / Format / Authentication** | `GET` | `JSON` | No public authentication required                                                                                                |
| **Parameters**                       | `tr` (search term), `lc` (location), `page` (page)                                                                                                |
| **Returned Fields**                  | ID, title, company, location, work arrangement, job link (description is partial)                                                                 |
| **Pagination Behavior**              | The response contains the `pagination.total_pages` key. The collector reads the total and schedules requests from `page=1` through `total_pages`. |

---

### 2.6 Quero Vagas Tech

* **Main Endpoint:** `GET https://querovagastech.com.br/api/jobs`
* **Details Endpoint:** `GET https://querovagastech.com.br/api/jobs/{id}`
* **Example Request:** `GET https://querovagastech.com.br/api/jobs?page=1&pageSize=100&sort=postedAt:desc`

| Parameter / Attribute                | Technical Detail / Value                                                                                                             |
| :----------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------- |
| **Method / Format / Authentication** | `GET` | `JSON` | No authentication required                                                                                          |
| **Parameters**                       | `page` (page), `pageSize` (max. 100), `sort` (sorting, e.g., `postedAt:desc`)                                                        |
| **Returned Fields**                  | `id`, title, company, `postedAt`, work arrangement, location                                                                         |
| **Pagination Behavior**              | Uses `page` + `pageSize`. To obtain the complete description and additional data, a secondary call to `/api/jobs/{id}` is performed. |

---

## 3. 📊 Summary Comparison Matrix

| Criterion / API             |     Meu Padrinho    |         Gupy        |      InHire     |     Solides     |      Trampos.co     |   Quero Vagas Tech  |
| :-------------------------- | :-----------------: | :-----------------: | :-------------: | :-------------: | :-----------------: | :-----------------: |
| **HTTP Method**             |        `GET`        |        `GET`        |      `GET`      |      `GET`      |        `GET`        |        `GET`        |
| **JSON Response**           |          ✅          |          ✅          |        ✅        |        ✅        |          ✅          |          ✅          |
| **Authentication Required** |         ❌ No        |         ❌ No        |       ❌ No      |       ❌ No      |         ❌ No        |         ❌ No        |
| **Limit per Request**       |    Not identified   |         100         |       N/A       |   25 (`take`)   |    Not identified   |         100         |
| **Pagination Mechanism**    |        `page`       |       `offset`      |       N/A       |      `page`     |        `page`       |        `page`       |
| **Keyword Search**          |          ❌          |     ✅ `jobName`     |        ❌        |    ✅ `title`    |        ✅ `tr`       |          ❌          |
| **Seniority Filter**        |      ✅ `niveis`     |          ❌          |        ❌        |        ❌        |          ❌          |          ❌          |
| **Description Included**    | Additional endpoint |          ✅          |        ❌        |        ✅        |       Partial       | Additional endpoint |
| **Unique Identifier**       |      `nano_id`      |         `id`        |     `jobId`     |        ID       |          ID         |         `id`        |
| **Main Limitation**         |  Separate endpoints | No major limitation | Requires Tenant | `take=25` limit | Partial description |    No text search   |

---

## 4. ⚙️ Data Collection and Data Engineering Pipeline

1. **List Ingestion:** The collector makes sequential requests to the main source (**Meu Padrinho**), incrementing the pagination (`page=1`, `page=2`, ...).

2. **Details and Skills Collection:** For each job, the system extracts the `nano_id` and makes parallel requests to `/api/vagas/{nano_id}` (description, location, salary) and `/api/vagas/{nano_id}/tecnologias`.

3. **Data Normalization:** All returned attributes are converted to the **Normalized Schema** defined in Section 1.

4. **Incremental Deduplication (Upsert):**

   * The system checks the `nano_id` in the database.
   * If it already exists, the job data is updated.
   * If it is new, the record is inserted with `status = ACTIVE`.

5. **Inactivation:** Jobs that no longer appear in successive scans are marked as `INACTIVE`.
