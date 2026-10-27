# ADR-002: APiBR as the MVP source

- **Status:** Accepted, subject to the documented completeness clarification

## Context

The source-selection record reports Gupy access uncertainty and pagination and
coverage limitations for Meu Padrinho. It identifies APiBR as the selected
primary MVP source and records its API details and alternatives in
[`docs/data/mvp-source-selection.md`](../../data/mvp-source-selection.md).

## Decision

Use APiBR as the initial primary job source. Additional adapters may be selected
later. Prefer sequential API scans and honor source usage constraints.

## Alternatives considered

Gupy, Meu Padrinho, InHire, Solides, Trampos.co, and Quero Vagas Tech were
considered or ruled out in the source-selection record. The reported reasons
and evidence remain there; this ADR does not strengthen unverified hypotheses.

## Rationale

The recorded comparison selected APiBR based on availability and feasibility
for the MVP, while acknowledging source coverage and payload limitations.

## Consequences and unresolved clarification

APiBR coverage and body formats constrain ingestion. Whether a completed APiBR
scan is a provably complete snapshot, and therefore safe to use for absence-based
stale transitions, must be clarified before implementing that behavior. See
[future PR clarifications](../../../specs/feature-001-mvp/acceptance.md).
