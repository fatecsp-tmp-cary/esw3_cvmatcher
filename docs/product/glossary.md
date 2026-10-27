# Glossary

| Term | Meaning |
|---|---|
| CandidateProfile | Validated, request-scoped representation of structured CV data. |
| Job | Canonical source-specific job record defined in the [MVP spec](../../specs/feature-001-mvp/spec.md). |
| Source identity | `(platform, source_job_id)` identifying one source record; not cross-source deduplication. |
| Incremental source | Returns new or changed records; absence does not imply expiration. |
| Snapshot source | A successful complete scan represents its covered set; only then may absence mark jobs stale. |
| STALE | Missing from a successful complete snapshot, but not confirmed unavailable. |
| EXPIRED | Confirmed unavailable; retained as history and excluded from active retrieval. |
| Compatibility score | Deterministic ranking score in `[0,100]`; not an employment probability. |
| Geographic eligibility | A decision to exclude by location; prohibited by the product invariants. |
