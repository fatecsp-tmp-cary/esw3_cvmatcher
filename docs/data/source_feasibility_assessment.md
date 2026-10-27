# Task #15 — Constraints and Source Feasibility Assessment

**Owner:** Kauan Baptiston Gassi  
**Project:** CV-Match — Software Engineering III  
**Status:** Technical evaluation only; terms and retention verification remain pending. This evaluation does not grant permission to ingest or store source data.

## Objective
Verify that candidate job sources can be used safely and reliably in the MVP, recording access requirements, terms of use, rate limits, storage/retention constraints, and operational risks (Fulfilling DoD for Issue #15 / Parent Issue #2).

## Sources and Evidence
- **Normalization Documentation (Task #14):** `docs/data/APIs_normalization.md` (source evaluation; not all evaluated sources are selected for the MVP).
- **Primary Source Swagger (APiBR):** https://apibr.com/vagas/swagger/ and https://apibr.com/vagas/api/v2/
- **Issue #15:** https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/15
- **Contribution Guidelines:** `CONTRIBUTING.md` (`dev` branch)

> **Important:** Public endpoints and JSON responses do not constitute formal authorization for automated scraping, redistribution, or permanent storage. The performed tests confirm technical feasibility, while official terms of service and contractual aspects remain under verification.

---

## Source Evaluation Matrix (Selected Initial Source and Other Evaluated Sources)

| Source | Role in MVP | Access Requirements / Auth | Technical Limits / Rate Limit / Polling | Storage Constraints & Terms | Risk and Decision |
|---|---|---|---|---|---|
| **APiBR (Vagas Aggregator)** | **Selected initial source** | `GET /vagas/api/v2/issues`<br>No authentication identified | Pagination observed up to `page=31`; `limit` parameter fixed/ignored. Official rate limit and polling rules unpublished. | Terms of use and retention under verification. Data based on GitHub issues. | **Approved as Official Primary Source for MVP.** Features structured metadata and labels useful for the unified schema. |
| **Meu Padrinho / API Vagas Tech** | Evaluated; not selected for initial integration | `GET /api/vagas`, `/detalhes`, and `/tecnologias`<br>No authentication identified | **Broken Pagination:** Only `page=0` works (~10 jobs); `page>=1` returns HTTP 204. Official rate limit unknown. | Official terms, polling policy, and retention authorization unconfirmed. | Not selected for initial integration; observed filters do not establish approval to ingest. |
| **Solides** | Evaluated; not selected initially | `GET /jobs/v3/portal-vacancies`<br>No authentication identified | Supports `title`, `page`, and `take=25`. Rate limits/time constraints unbudgeted. | Official terms of service and redistribution/retention authorization unconfirmed. | Candidate for possible future selection. |
| **Trampos.co** | Evaluated; not selected initially | `GET /api/v2/opportunities`<br>No authentication identified | Supports `tr`, `lc`, and `page`. Returns `total_pages`. Partial description in job listing. | Terms of use and retention unconfirmed officially. | Candidate for possible future selection; descriptions are partial. |
| **Quero Vagas Tech** | Evaluated; not selected initially | `GET /api/jobs` and `GET /api/jobs/{id}`<br>No authentication identified | Supports `page`, `pageSize` (up to 100), and `sort`. Requires secondary endpoint call for full details. | Terms of use and retention unconfirmed officially. | Candidate for possible future selection; detail calls increase request volume. |
| **InHire** | Evaluated; not selected initially (tenant-based) | `GET /job-posts/public/pages`<br>**Required Header:** `X-Tenant` | No global search or pagination. Depends on predefined tenant company list (e.g., `magalu`). | Per-tenant terms of service and official limits unrecorded. | Any future use requires tenant mapping and separate selection. |
| **Gupy** | **EXCLUDED FROM MVP** | `GET employability-portal.gupy.io` | **API Unavailable / Obsolete.** | N/A | **Excluded from MVP scope** due to API unavailability and public endpoint changes. |

---

## Definition of Done (DoD) Fulfillment

### 1. API Requirements, Terms, and Authentication
- **Authentication:** No API keys or auth tokens were identified for evaluated sources in testing (with the exception of the `X-Tenant` header required by InHire).
- **Terms & License:** Most endpoints do not supply explicit terms within their JSON payload. Clarification requests and legal review remain necessary before full production rollouts.

### 2. Request Limits (Rate Limits) and Polling Constraints
- **Official Rate Limits:** In the absence of published rate limits per minute/hour, the system assumes conservative polling policies (never interpreting unstated limits as "unlimited access").
- **Polling & Resiliency Strategy:**
  - Implementation of **Exponential Backoff** and strict compliance with the `Retry-After` HTTP header.
  - Native handling of HTTP status codes `429` (Too Many Requests) and `5xx`.
  - Sequential ingestion controlled by safe time intervals.

### 3. Storage Restrictions, Retention, and Deduplication
- **Storage:** This evaluation does not establish storage permission. Retain data only as allowed by source terms and map it to the canonical job fields: `platform`, `source_job_id`, `publication_date`, and lifecycle `status`.
- **Privacy (LGPD / GDPR):** Do not store candidate personal data or personal contact details found in job descriptions.
- **Deduplication & Job Identity Rule:**
  - **Source identity (Upsert):** Use the unique pair `platform` + `source_job_id`; this represents source identity, not cross-source deduplication.
  - **Inter-Source Independence (No cross-merging):** As aligned in `CONTRIBUTING.md`, job postings from different platforms **are not merged or consolidated**, even if titles or companies match. Each platform record remains independent.

---

## Operational Risks and Mitigation Strategy

| Operational Risk | System Impact | Mitigation Strategy |
|---|---|---|
| **Endpoint changes or downtime** | Ingestion pipeline failure | Defensive timeouts, error logging, health checks, and API contract testing. |
| **Rate Limit Blocking (HTTP 429)** | Ingestion process stalled | Spaced polling intervals, circuit breakers, and `Retry-After` header handling. |
| **Pagination Defect (e.g., Meu Padrinho `page>=1` = 204)** | Incomplete data collection | Do not include this source in the initial integration; any future selection should account for the observed pagination defect. |
| **Obsolete / Closed Job Postings** | Displaying inactive listings | Only successful complete snapshots can mark absent jobs `STALE`; failed polls and incremental absence do not change lifecycle state. Apply the configured expiration policy. |
| **Job text containing PII** | Non-compliance with privacy regulations | Text sanitization and stripping of personal emails/phone numbers before persistence. |

---

## Summary and Conclusion
The evaluation supports APiBR as the selected initial source based on observed technical behavior. Other sources are candidates, not selected integrations. Technical feasibility does not establish permission to store or redistribute data; verification remains pending.
