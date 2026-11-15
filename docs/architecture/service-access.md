# Production service access

Current rate interval and pre-production scope: [ADR-010](decisions/ADR-010-preproduction-and-minute-rate-limit.md).

Original access decision: [ADR-009](decisions/ADR-009-open-api-global-rate-limit.md), accepted
in the implementation interview on 2026-11-11.

The intended integration is the trusted Sistema Currículo backend, server to
server. The user nevertheless selected an **open API with no authentication**.
Browser CORS remains disabled; HTTPS remains required. Do not add API keys,
browser login or identity-provider dependencies implicitly.

The production ASGI entry point `src.api.app:app` applies a PostgreSQL-backed
60-requests/minute global rolling admission limit to all HTTP paths. Excess
requests return 429 with Retry-After: 60; unavailable admission state returns
privacy-safe 503. Migrate the database before starting the API. All replicas
must share the same database for a service-wide quota. This does not change the
curriculum DTOs, matching response or validation privacy policy.

`create_app()` is a dependency-injection factory: tests may omit its limiter;
production composition must supply the shared limiter. The module entry point supplies it. The local deterministic mock remains separate. Health and docs count
against the global quota. No client/IP identity is stored by rate limiting.

Limiter implementation and independent-connection concurrency tests are present.
HTTPS termination, production deployment and realistic load verification remain
pending; the quota alone is not a throughput guarantee.

The module application composes `production_matches` and `production_ready`
from `src/api/runtime.py`. Database/session/model construction is lazy and shared;
serving never downloads models. Matching and health map recognized database
connection/pool outages and typed missing local-model dependencies to privacy-safe
503 responses. Missing/invalid database configuration is handled at composition.
Unexpected normalization, scoring or encoder-result errors reach the existing
privacy-safe 500 handler, which logs only exception type and source location.
Processing-budget failures retain their fixed-category 503 behavior. This changes
neither anonymous admission nor the shared quota's inclusion of health requests.
Worker/Compose integration and independent quality/release acceptance remain
separate stack steps and gates.
