# ADR-007: Canonical persistence alignment and source identity

- **Status:** Accepted
- **Date:** 2026-11-07

## Context

Canonical Job fields and lifecycle states must be consistent across domain
and persistence. Source identity is distinct from adapter configuration;
schema corrections must support existing databases.

## Decision

Enforce unique `(platform, source_job_id)`
identity and reject missing/blank IDs. The surrogate `id` identifies the
persisted job; `source_id` remains SQL-only adapter/polling metadata referencing
`job_sources`, outside canonical Job data and API responses. Other additional
persisted state stays in separate structures under the existing invariant.

Preserve the original migration and apply corrective migrations for canonical
columns, the four-state lifecycle, source-run evidence and skill/requirement
structures. Keep the explicit unique identity constraint. Retain expired
records. `EXPIRED` is terminal; only `STALE` can
reactivate from confirmed rediscovery, within the existing transition graph.

## Alternatives considered

Rewrite the initial migration, identify jobs solely by the adapter configuration,
or include adapter configuration in the canonical Job. These would break upgrades for existing databases or conflate
independent
domain and operational identities. Allowing `EXPIRED → ACTIVE` would violate
the terminal lifecycle state.

## Rationale and consequences

Source-specific identity and history remain stable without cross-source merging.
The corrective downgrade maps `DISCOVERED`/`STALE` to `ACTIVE`, because the old
two-value enum cannot express them; it also drops the newly added columns.
This is a lossy schema rollback, not a lifecycle operation. PostgreSQL migration
round trips must test existing rows and source-run backfill. Concurrent polling
and atomic upsert safety remain production follow-up work.
