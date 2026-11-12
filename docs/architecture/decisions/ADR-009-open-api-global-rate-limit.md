# ADR-009: Open API with global admission limit

- **Status:** Accepted
- **Date:** 2026-11-11
- **Authority:** Implementation interview: the user selected no authentication,
  then clarified 60 requests/second globally across the service.
- **Supersedes:** Earlier production-authentication requirements in the MVP
  spec/acceptance and the pending authentication mechanism in service-access policy.

## Context

The intended integration is the Sistema Currículo backend, server to server.
The user explicitly chose an open API despite that intended caller boundary.
The canonical curriculum payload and privacy requirements remain unchanged.

## Decision

Production HTTP API access requires no credentials. Keep HTTPS and browser CORS
disabled. Enforce at most 60 admitted HTTP requests in any rolling one-second
window across the service, including all API processes/replicas that use the same
application database. Requests exceeding the limit return a privacy-safe RFC 9457
429 response with Retry-After: 1. All paths count, including health, docs and
invalid/unmatched requests; rejected requests do not consume an admission slot.

Coordinate admission through PostgreSQL, retaining only admission timestamps.
Serialize admission with a transaction advisory lock, read database time after
locking, expire old entries, count and insert atomically. Do not store IPs,
candidate data, headers or credentials. An unavailable admission store fails
closed with a generic 503; do not silently fall back to a per-process limiter.
Apply the limiter before body validation. The production ASGI entry point enables
it; the dependency-injected application factory supports isolated contract tests
without a database. The separate deterministic local mock remains independent.

## Alternatives

Shared API keys, identity-provider tokens and mutual TLS were offered; the user
selected no authentication. A per-IP quota was offered; the user selected one
global quota. Per-process counters would multiply the allowance with worker
count. A separate Redis dependency conflicts with the PostgreSQL-only state
boundary and is unnecessary for this quota.

## Consequences

Every admitted or rejected production request needs PostgreSQL admission
coordination. All production replicas must share this database and limiter.
Migrate before serving. Requests may receive 503 if the limiter is unavailable,
including health checks. The admission limit is not a concurrency bound or a
claim of capacity for 60 expensive matching requests per second. HTTPS termination
and production deployment/load verification remain pending.
