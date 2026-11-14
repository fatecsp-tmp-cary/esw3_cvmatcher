# Production service access

Current rate interval and pre-production scope: [ADR-010](decisions/ADR-010-preproduction-and-minute-rate-limit.md).

Original access decision: [ADR-009](decisions/ADR-009-open-api-global-rate-limit.md), accepted
in the implementation interview on 2026-11-11.

The intended integration is the trusted Sistema Currículo backend, server to
server. The user nevertheless selected an **open API with no authentication**.
Browser CORS remains disabled; HTTPS remains required. Do not add API keys,
browser login or identity-provider dependencies implicitly.

The required production policy is for `src.api.app:app` to apply a PostgreSQL-backed
60-requests/minute global rolling admission limit to all HTTP paths. Excess
requests return 429 with Retry-After: 60; unavailable admission state returns
privacy-safe 503. Migrate the database before starting the API. All replicas
must share the same database for a service-wide quota. This does not change the
curriculum DTOs, matching response or validation privacy policy.

`create_app()` is a dependency-injection factory: tests may omit its limiter;
production composition must supply the shared limiter. That wiring is pending
in stack PR #166. The local deterministic mock remains separate. Health and docs count
against the global quota. No client/IP identity is stored by rate limiting.

Limiter implementation and independent-connection concurrency tests are pending
in stack PR #166. This branch does not enforce the quota.
HTTPS termination, production deployment and realistic load verification remain
pending; the quota alone is not a throughput guarantee.
