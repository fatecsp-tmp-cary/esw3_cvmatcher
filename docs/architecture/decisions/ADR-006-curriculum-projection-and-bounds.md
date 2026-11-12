# ADR-006: Curriculum projection and collection bounds

- **Status:** Accepted
- **Date:** 2026-11-07

## Context

The internal profile must represent every valid public request, including
empty sections and source text bounds. Collection counts need explicit service
limits to bound input processing.

## Decision

Use Sistema Currículo's preview matching projection, as
specified in [acceptance](../../../specs/feature-001-mvp/acceptance.md):
`curriculo_id`, `formacoes`, `experiencias`, `projetos`, `competencias`, and
`idiomas`, with source dates, levels, and string project technologies.
Reject section-item IDs and identity/contact/presentation fields. Keep
`POST /matches`, `limit`, RFC 9457 errors, and response job identity,
eligibility, match details and model/algorithm metadata. The executor boundary
remains `CurriculumRequest, limit`; the complete pipeline is separate work.

Align the internal profile to every valid public request. Require all five arrays,
allow empty arrays, and cap competencies at 200, experiences/projects at 50
each, and education/languages at 20 each. These service caps are explicit
projection constraints, not assertions about upstream collection limits.

The transient adapter preserves every matching section, competency level,
education level/status, project text, and calendar date, without copying the
curriculum UUID. Empty sections produce empty matching fields; do not invent
skills, role context, location, seniority or preferences. Internal text limits
must not reject valid public input. Production and mock share the schema.

## Alternatives considered

A flat DTO, mandatory skills/role context, or dropped sections would lose
valid preview content. Uncapped arrays would leave processing unbounded by
collection count. Using different production/mock schemas risks drift.

## Rationale and consequences

This preserves the confirmed integration boundary and makes input processing
bounded by collection count. Requests over the caps receive privacy-safe 422
problem responses; callers must reduce oversized collections. Source-valid
text fields keep their existing bounds; body size and inference-time budgets
remain follow-up operational work. Empty profiles require the future pipeline
to define conservative empty-evidence behavior, not fabricate candidate data.
