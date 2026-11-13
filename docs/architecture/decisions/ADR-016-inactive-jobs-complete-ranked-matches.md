# ADR-016: Inactive jobs complete the ranked matches after active jobs

- **Status:** Accepted
- **Date:** 2026-11-12
- **Authority:** Tech lead decision, after the two orderings below were compared.
- **Supersedes:** The statements that only `ACTIVE` jobs are eligible for
  matching retrieval and that expired jobs are excluded from retrieval, in the
  MVP spec/acceptance, the invariants and the textual retrieval notes. Readiness,
  privacy, determinism and the no-geographic-filtering rules remain unchanged.

## Context

Matching retrieved only `ACTIVE` jobs. Under ADR-015 a job that leaves the source
listing becomes `STALE`, and a closed job is `EXPIRED`; both then disappeared from
the response, even when highly compatible, and a request could receive fewer
results than its `limit`. The requested behavior is to return those jobs as
well, with active jobs first.

The frozen response contract already carries a boolean `eligibility`, defined as
matching eligibility and never geography. It was `true` for every result.

## Decision

`POST /matches` ranks two groups in order:

1. **Active group:** `ACTIVE` jobs, retrieved and scored exactly as before.
2. **Inactive group:** every other status (`DISCOVERED`, `STALE`, `EXPIRED`),
   retrieved and scored by the same stages and the same score.

The inactive group is evaluated only when the active group returns fewer than
`limit` results, and it only fills the remaining positions. Every active result
precedes every inactive result regardless of score. Rank numbers continue
across the groups. Active results carry `eligibility: true`; inactive results
carry `eligibility: false`. Within a group the existing deterministic order
applies: score, then platform, source job ID and ID.

Both groups require current successful extraction and embedding provenance. The
response shape, score range and meaning, versions and privacy rules do not
change. Location and work arrangement still never filter or score eligibility.

## Alternatives considered

- **Score bonus for active jobs.** A highly compatible inactive job could then
  outrank an active one. Rejected: it does not guarantee active jobs first, and
  it makes the score mean something other than compatibility.
- **A new status field in the response.** Rejected: the public contract is
  frozen and `eligibility` already expresses whether a result is a currently
  eligible match.
- **Keep active-only retrieval.** Rejected by the requested behavior.

## Rationale and consequences

Grouping keeps the active path unchanged, including its partial indexes and
latency, because the second group runs only when the first does not fill the
limit. The score keeps a single meaning in both groups.

Consumers must read `eligibility`: a result with `false` is historical or
unverified and may no longer accept applications. When at least `limit` active
jobs are ready, no inactive job is returned. Background processing still skips
`EXPIRED` jobs, so an expired job appears only if it was extracted and embedded
before it expired and its content and model versions are still current. The
inactive group has no dedicated index and is scanned sequentially; it is
bounded by the same retrieval limit.
