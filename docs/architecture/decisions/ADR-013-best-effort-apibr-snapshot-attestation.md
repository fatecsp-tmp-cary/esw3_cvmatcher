# ADR-013: Best-effort APiBR health/count snapshot attestation

- **Status:** Accepted
- **Date:** 2026-11-12
- **Authority:** User proposed APiBR health record counts and explicitly selected
  the documented best-effort completeness rule after its limitations were explained.
- **Supersedes:** The blanket unproven/incomplete APiBR snapshot conclusion in
  ADR-002/003, only when the conditions below all hold. Other availability,
  partial-run, retention and lifecycle rules remain unchanged.

## Context

`GET https://apibr.com/vagas/api/v2/health` exposes
`checks.dataset_issues_body.details.records` and `last_updated`, but no immutable
snapshot identifier. The bounded 2026-11-12 probe observed 728 distinct issue IDs,
eight nonempty pages followed by an empty page, stable healthy count/timestamp,
no duplicates and no normalization rejection. Only aggregate evidence was retained:
[probe](../../reports/2026-11-12-apibr-count-attestation.json). Every observed job
lacked explicit availability and remains DISCOVERED; completeness is not openness.

## Decision

For explicitly configured SNAPSHOT polling, bracket the issues-with-body scan
with bounded health reads. A scan may set `snapshot_complete=true` only if:

1. Both service/body-dataset health checks are healthy, not from backup, with a
   valid nonnegative integer record count and timezone-aware update timestamp.
2. That count and update timestamp are identical before and after the scan.
3. Exactly that many distinct canonical source IDs were collected. Greater counts
   do not qualify; duplicates cannot inflate coverage.
4. A terminal empty page was reached, without page-cap truncation or cancellation.
5. There were no invalid IDs, normalization/persistence rejections or request
   failures, including failures subsequently recovered by retry.

Missing/malformed health or unsupported uninstrumented clients never qualify.
Exhausted health transport failures propagate and roll back the poll under ADR-003;
a recovered retry still disqualifies completeness even when payload polling succeeds.
Incremental configurations remain incomplete and do not acquire snapshot authority
from a count match. Preserve disabled-by-default raw retention and safe error
categories. Store bounded health signatures/counts/policy version in supporting
SourceRun metadata, outside fixed canonical Job fields; retain no response bodies
or ID collections there. Keep source polling locks over the entire operation.

This is a best-effort attestation, **not an atomic consistency proof**. Equal
counts/timestamps can miss concurrent rewrites or a source implementation defect.
The user accepted this limitation after being offered diagnostic-only treatment.
Record the policy version so future source guarantees can supersede it explicitly.

## Alternatives and impact

A raw count greater than or equal to health records was considered insufficient:
it can include duplicates, drift or unrelated generations. Diagnostic-only use
pending an immutable source-generation contract was offered and rejected in favor
of the stricter best-effort rule. An immutable dataset hash/version or consistent
snapshot token would provide stronger evidence if the provider adds it.

Snapshot completeness does not verify availability, source usage/retention rights,
or permit a hidden GitHub verifier. This change does not enable absence-driven
stale/expiration policy; #145 still owns its thresholds/counters and evidence.
The #125 regression criterion now covers qualifying versus incomplete attestation,
explicit expiration, stale rediscovery and preservation of availability on failure.
No production deployment is authorized. Migration b1e006 adds nullable JSONB
snapshot evidence to SourceRun; historical migrations/decisions are preserved.
