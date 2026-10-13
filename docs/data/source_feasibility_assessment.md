# Task #15 — Constraints and Source Feasibility Assessment

**Owner:** Kauan Baptiston Gassi  
**Project:** CV-Match — Software Engineering III  
**Status:** Documented and Technical Evaluation Updated (Aligned with Task #14); Legal/Terms Verification Pending Before Production Approval.

## Objective
Verify that candidate job sources can be used safely and reliably in the MVP, recording access requirements, terms of use, rate limits, storage/retention constraints, and operational risks (Fulfilling DoD for Issue #15 / Parent Issue #2).

## Sources and Evidence
- **Normalization Documentation (Task #14):** `docs/reports/APIs_normalization.md` (6 sources evaluated and retained for MVP + Gupy exclusion).
- **Primary Source Swagger (APiBR):** https://apibr.com/vagas/swagger/ and https://apibr.com/vagas/api/v2/
- **Issue #15:** https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/issues/15
- **Contribution Guidelines:** `CONTRIBUTING.md` (`dev` branch)

> **Important:** Public endpoints and JSON responses do not constitute formal authorization for automated scraping, redistribution, or permanent storage. The performed tests confirm technical feasibility, while official terms of service and contractual aspects remain under verification.

---

## Source Evaluation Matrix (6 Retained Sources + Excluded Gupy)

| Source | Role in MVP | Access Requirements / Auth | Technical Limits / Rate Limit / Polling | Storage Constraints & Terms | Risk and Decision |
|---|---|---|---|---|---|
| **APiBR (Vagas Aggregator)** | **Official Primary Source** | `GET /vagas/api/v2/issues`<br>No authentication identified | Pagination observed up to `page=31`; `limit` parameter fixed/ignored. Official rate limit and polling rules unpublished. | Terms of use and retention under verification. Data based on GitHub issues. | **Approved as Official Primary Source for MVP.** Features structured metadata and labels useful for the unified schema. |
| **Meu Padrinho / API Vagas Tech** | **Complementary Source** | `GET /api/vagas`, `/detalhes`, and `/tecnologias`<br>No authentication identified | **Broken Pagination:** Only `page=0` works (~10 jobs); `page>=1` returns HTTP 204. Official rate limit unknown. | Official terms, polling policy, and retention authorization unconfirmed. | **Demoted to Complementary Source.** Ingestion restricted to recent jobs via seniority filters (`niveis`). |
| **Solides** | Potential Complementary | `GET /jobs/v3/portal-vacancies`<br>No authentication identified | Supports `title`, `page`, and `take=25`. Rate limits/time constraints unbudgeted. | Official terms of service and redistribution/retention authorization unconfirmed. | Technically viable complementary source for future iterations. |
| **Trampos.co** | Potential Complementary | `GET /api/v2/opportunities`<br>No authentication identified | Supports `tr`, `lc`, and `page`. Returns `total_pages`. Partial description in job listing. | Terms of use and retention unconfirmed officially. | Potential complementary source; requires attention due to partial job descriptions. |
| **Quero Vagas Tech** | Potential Complementary | `GET /api/jobs` and `GET /api/jobs/{id}`<br>No authentication identified | Supports `page`, `pageSize` (up to 100), and `sort`. Requires secondary endpoint call for full details. | Terms of use and retention unconfirmed officially. | Potential complementary source; higher request volume due to detail calls. |
| **InHire** | Complementary / Tenant-Based | `GET /job-posts/public/pages`<br>**Required Header:** `X-Tenant` | No global search or pagination. Depends on predefined tenant company list (e.g., `magalu`). | Per-tenant terms of service and official limits unrecorded. | Complementary source conditioned on mapping partner companies beforehand. |
| **Gupy** | **EXCLUDED FROM MVP** | `GET employability-portal.gupy.io` | **API Unavailable / Obsolete.** | N/A | **Excluded from MVP scope** due to API unavailability and public endpoint changes. |

---

## Definition of Done (DoD) Fulfillment

### 1. API Requirements, Terms, and Authentication
- **Authentication:** None of the 6 retained sources require API keys or auth tokens in testing (with the exception of the `X-Tenant` header required by InHire).
- **Terms & License:** Most endpoints do not supply explicit terms within their JSON payload. Clarification requests and legal review remain necessary before full production rollouts.

### 2. Request Limits (Rate Limits) and Polling Constraints
- **Official Rate Limits:** In the absence of published rate limits per minute/hour, the system assumes conservative polling policies (never interpreting unstated limits as "unlimited access").
- **Polling & Resiliency Strategy:**
  - Implementation of **Exponential Backoff** and strict compliance with the `Retry-After` HTTP header.
  - Native handling of HTTP status codes `429` (Too Many Requests) and `5xx`.
  - Sequential ingestion controlled by safe time intervals.

### 3. Storage Restrictions, Retention, and Deduplication
- **Storage:** Persistence of normalized fields into the unified database is permitted (`source_job_id`, `platform`, `title`, `company`, `description`, `location`, `work_arrangement`, `seniority_level`, `skills`, `salary`, `job_url`, `publication_date`, `source_status`).
- **Privacy (LGPD / GDPR):** Do not store candidate personal data or personal contact details found in job descriptions.
- **Deduplication & Job Identity Rule:**
  - **Intra-Platform Technical Deduplication (Upsert):** Deduplication occurs strictly within the same source using the unique pair `source_job_id` + `platform`. If an APiBR job already exists, its record is updated.
  - **Inter-Source Independence (No cross-merging):** As aligned in `CONTRIBUTING.md`, job postings from different platforms **are not merged or consolidated**, even if titles or companies match. Each platform record remains independent.

---

## Operational Risks and Mitigation Strategy

| Operational Risk | System Impact | Mitigation Strategy |
|---|---|---|
| **Endpoint changes or downtime** | Ingestion pipeline failure | Defensive timeouts, error logging, health checks, and API contract testing. |
| **Rate Limit Blocking (HTTP 429)** | Ingestion process stalled | Spaced polling intervals, circuit breakers, and `Retry-After` header handling. |
| **Pagination Defect (e.g., Meu Padrinho `page>=1` = 204)** | Incomplete data collection | Limit ingestion to functional filters (`page=0` + `niveis`) and prioritize APiBR as primary source. |
| **Obsolete / Closed Job Postings** | Displaying inactive listings | Periodically update `source_status` (`ACTIVE`, `INACTIVE`, `UNAVAILABLE`) and auto-expire stale jobs. |
| **Job text containing PII** | Non-compliance with privacy regulations | Text sanitization and stripping of personal emails/phone numbers before persistence. |

---

## Summary and Conclusion
The evaluation confirms the **technical and architectural feasibility** of **APiBR as the official primary source for the MVP**, complemented by **Meu Padrinho** and the other sources mapped in Task #14. **Gupy has been officially removed**. The ingestion strategy satisfies all operational requirements outlined in Issue #15, ensuring robustness and compliance in data handling.
