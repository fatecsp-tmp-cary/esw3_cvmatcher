# ADR-001: Core privacy, source identity, and matching boundaries

- **Status:** Accepted

## Context

The API handles personal CV data and combines jobs from multiple independent
sources. Geographic filtering, candidate persistence, and cross-source merging
are excluded from the product scope.

## Decision

Candidate profiles, candidate embeddings, and match results remain transient
and are never persisted or logged. Each source job remains independent, with
source-specific identity. Matching may use location/mode as descriptive signals
but must not classify or filter geographic eligibility. Ranking is deterministic
for fixed inputs and versions. PostgreSQL is the only application-state store.

## Alternatives considered

Persist candidate profiles/results; merge likely duplicate listings; use
location as a hard eligibility filter; introduce a separate broker/state store.
These alternatives conflict with privacy, scope, or the local-first architecture.

## Rationale and consequences

This keeps candidate data transient, makes source provenance explicit, and
preserves the stated matching boundary. It limits personalization/history and
requires worker coordination and durable state to use PostgreSQL. Any change
requires a superseding ADR and explicit approval before implementation.
