# ADR-015: Absence from a qualifying APiBR snapshot marks jobs STALE

- **Status:** Accepted
- **Date:** 2026-11-12
- **Authority:** Tech lead decision, after ADR-014 made listed APiBR jobs `ACTIVE`
  and left no rule that deactivates a job removed from the listing.
- **Supersedes:** The statements in ADR-013 and the supporting source documents
  that a qualifying snapshot does not enable any absence-driven transition.
  ADR-013's qualification conditions and all other rules remain unchanged.

## Context

Under ADR-014, presence in the APiBR open-vacancy listing makes a job `ACTIVE`.
The source removes closed vacancies from that listing, so without an absence
rule a closed vacancy stays `ACTIVE` and remains in matching indefinitely. The
[MVP spec](../../../specs/feature-001-mvp/spec.md) already defines `STALE` as
absence from a successful complete snapshot, and ADR-013 defines when an
explicitly configured APiBR SNAPSHOT scan qualifies as complete. The transition
itself was never enabled: `jobs_absent` and `jobs_marked_stale` were always zero.

## Decision

When a SNAPSHOT poll finishes `SUCCEEDED` and its attestation qualifies under
ADR-013, every `ACTIVE` job of the polled source that was not observed in that
scan becomes `STALE`. One qualifying snapshot is sufficient. The run records
`jobs_absent` (non-expired jobs of the source not observed) and
`jobs_marked_stale` (jobs newly marked).

Incremental, partial, failed and non-qualifying scans never mark absence. Jobs
of other sources are never touched. `DISCOVERED` and `EXPIRED` jobs are not
changed by absence. Rediscovery in a later poll reactivates a `STALE` job, as
before. `STALE` jobs stay stored and are excluded from matching by the existing
active-only retrieval.

## Alternatives considered

- Require several consecutive qualifying snapshots before `STALE`. Safer against
  a transient source defect, but needs per-job counters outside the canonical
  job and delays removal by days with a daily poll. The transition is reversible
  on rediscovery, so one snapshot was accepted.
- Expire absent jobs directly. Rejected: `EXPIRED` is terminal, and the
  best-effort attestation of ADR-013 is not an atomic consistency proof.
- Verify each absent job on GitHub (#153). Stronger evidence, but needs a token
  and per-job requests; it remains possible as additional evidence.

## Rationale and consequences

`STALE` is the reversible state the spec reserves for exactly this evidence, so a
false absence caused by a concurrent source rewrite is corrected by the next
poll that lists the job again. The best-effort limits of ADR-013 still apply: a
qualifying count can miss a concurrent rewrite.

Thresholds for `STALE→EXPIRED` (consecutive missing snapshots and maximum stale
duration) are not decided here and remain #145. The default source polling mode
stays INCREMENTAL, so this rule applies only to sources an operator explicitly
configures as SNAPSHOT.
