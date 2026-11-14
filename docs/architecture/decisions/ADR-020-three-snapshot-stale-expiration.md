# ADR-020: Three qualifying absence snapshots expire stale jobs

- **Status:** Accepted
- **Date:** 2026-11-14
- **Authority:** User interview following the extraction correction and branch decision audit.
- **Supersedes:** The pending maximum-stale-age/consecutive-missing threshold in #145; ADR-015 STALE semantics and all other lifecycle rules remain.
- **Implementation status:** Policy recorded; implementation and verification remain pending unless separately evidenced in feature tasks.

## Context

ADR-015 makes one qualifying absence snapshot mark an ACTIVE job STALE. Issue
#145 still needs an expiration threshold; EXPIRED remains terminal and records
remain stored under the existing lifecycle contract.

## Decision

Expire after three consecutive qualifying snapshots confirming absence, counting
the qualifying snapshot that first makes the job STALE as snapshot one. No age
or wall-clock expiration threshold is selected. Failed, partial, incremental and
non-qualifying scans do not advance the qualifying-absence count. They pause that
evidence sequence; confirmed rediscovery before expiration resets it and reactivates
the job. Count source-specific evidence only and never affect other sources.

Store supporting absence-count state outside canonical Job fields. EXPIRED remains
terminal and historical rows are retained. This adds no retention/deletion rule.
Where ADR-016's later inactive fallback applies, expiration does not itself prohibit
a previously processed/current-version expired job from appearing in that group.
No model/configuration failure or ordinary old last_seen_at establishes absence.

## Alternatives and rationale

Thirty days stale, either an age/count threshold and disabling automatic expiry
were offered. The user selected three confirming qualifying snapshots only. An age
trigger without fresh source evidence could turn an outage into expiration.

## Consequences

Implement #145 counters/transactions, reset on rediscovery, and regress first/
second/third snapshot boundaries, unusable scans, source isolation, idempotence,
readiness independence and terminal expiration. Existing reliable source timestamp
expiry is unchanged. ADR-015's one-snapshot STALE behavior is already implemented
on the source branch; this three-snapshot EXPIRED policy remains pending.
