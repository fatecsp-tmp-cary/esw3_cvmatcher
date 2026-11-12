# ADR-010: Pre-production scope and corrected rate-limit interval

- **Status:** Accepted
- **Date:** 2026-11-11
- **Authority:** User correction: no production deployment exists, no availability/
  consistency precautions are needed for model reprocessing, and the quota is
  60 requests per minute. Follow the agentic orchestration environment spec.
- **Supersedes:** ADR-009's per-second interval and pending rollout-availability
  decision. Other ADR-009 decisions remain, including no authentication and a
  global, anonymous PostgreSQL-backed quota.

## Decision

Admit at most **60 requests in any rolling 60-second window globally**. Return
privacy-safe 429 with Retry-After: 60 when exhausted; no authentication is added.
The retry header is a conservative full-window delay, not an exact earliest slot.

This project is pre-production. Model/configuration reprocessing may interrupt
availability: use a simple stop/reprocess/restart workflow. Do not require dual
model versions, zero-downtime cutovers or rolling-deployment consistency machinery.
Keep the previously accepted extraction-success readiness rule, explicit retry
policy, data privacy, source independence and deterministic fixed-version scoring.
Do not remove those application invariants under the availability clarification.

Use `/workspace/agentic-environment-spec.md` for the development orchestration
workflow. Continue application work on this host under the already approved
host exception; do not claim the absent orchestration runtime or Debian guest
has been deployed. Native delegation, isolated task worktrees, resource gates,
verification and evidence must follow that spec as tooling becomes available.

## Alternatives and consequences

The earlier per-second quota was explicitly corrected by the user. Elaborate
availability-preserving reprocessing is unnecessary before production exists.
Reprocessing interruptions are acceptable; deployment and performance claims
still require their own verification. This decision requires no schema migration:
the anonymous admission timestamps already support a 60-second interval.
