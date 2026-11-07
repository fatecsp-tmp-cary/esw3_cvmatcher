# ADR-006: Curriculum projection and collection bounds

- **Status:** Accepted
- **Date:** 2026-11-07

## Context

PRs #111/#112 conflict with the public contract already confirmed in #130.
The historical internal profile requires skills and role context and has text
bounds stricter than valid preview fields. The previous source-model decision
allowed uncapped collections; the user explicitly requested sensible collection
caps during the integration interview.

## Decision

Retain the implemented preview projection at source commit `66af300`, as
specified in [acceptance](../../../specs/feature-001-mvp/acceptance.md):
`curriculo_id`, `formacoes`, `experiencias`, `projetos`, `competencias`, and
`idiomas`, with source dates, levels, and string project technologies.
Reject section-item IDs and identity/contact/presentation fields. Keep
`POST /matches`, `limit`, RFC 9457 errors, and response job identity,
eligibility, match details and model/algorithm metadata. The executor boundary
remains `CurriculumRequest, limit`; the complete pipeline is separate work.

The user approved aligning the internal profile to every valid public request
and superseded the earlier uncapped-array policy. Require all five arrays,
allow empty arrays, and cap competencies at 200, experiences/projects at 50
each, and education/languages at 20 each. These service caps are explicit
projection constraints, not assertions about upstream collection limits.

The transient adapter preserves every matching section, competency level,
education level/status, project text, and calendar date, without copying the
curriculum UUID. Empty sections produce empty matching fields; do not invent
skills, role context, location, seniority or preferences. Internal text limits
must not reject valid public input. Production and mock share the schema.

## Alternatives considered

Restore the outdated flat integration-document DTO, retain the internal
skills/role requirements, drop unmatched sections, or keep uncapped arrays.
Those choices either conflict with the selected preview or the user's latest
collection-bound decision. Using different production/mock schemas risks drift.

## Rationale and consequences

This preserves the confirmed integration boundary and makes input processing
bounded by collection count. Requests over the caps receive privacy-safe 422
problem responses; callers must reduce oversized collections. Source-valid
text fields keep their existing bounds; body size and inference-time budgets
remain follow-up operational work. Empty profiles require the future pipeline
to define conservative empty-evidence behavior, not fabricate candidate data.
