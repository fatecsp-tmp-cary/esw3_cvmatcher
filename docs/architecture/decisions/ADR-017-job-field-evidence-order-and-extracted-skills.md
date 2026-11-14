# ADR-017: Evidence order for APiBR job fields and extracted skills in results

- **Status:** Proposed (draft PR for review)
- **Date:** 2026-11-12
- **Authority:** Requested by the tech lead after a local end-to-end run showed
  seniority, work arrangement and skills empty for most jobs. Pending review by
  the project maintainers.
- **Supersedes:** Nothing. It extends the exact-label mapping of #180 and the
  rule in the [extraction strategy](../../data/job-field-extraction.md) to prefer
  explicit structured source fields.

## Context

After #180 a field is filled only when an exact typed label matches a known
value. On the live listing of 2026-11-12 (729 jobs) that left seniority empty for
557 jobs, work arrangement for 302 and `skills` for 598, even when the job states
the value in its title or in an explicit body field. The worker already associates
skills with a job when a mention appears in an explicit requirement context, and
the matching score uses them, but the `skills` shown in a result contained only
label-derived skills.

## Decision

`seniority_level` and `work_arrangement` use the strongest available evidence:

1. **Typed labels** (as in #180).
2. **Explicit body fields:** an inline `Nível: pleno` or `Localização: Remoto`
   line, or a `Nível`/`Alocação` heading followed by options, where unchecked
   `[ ]` options are ignored. Only the names `Nível`, `Senioridade`, `Alocação`,
   `Modalidade` and `Local`/`Localização` are read; prose is never interpreted.
3. **A single recognizable word of the title.**

The first of (1) and (2) with exactly one distinct value wins. If explicit
evidence exists but is conflicting, the value is unknown and the title is not
consulted. The title is used only when neither labels nor body fields produced
any value, and only if it contains exactly one distinct value; a dotted name such
as `Remote.com` is one token, not the word it begins with. All mapping uses the
shared exact aliases, so unknown or ambiguous text stays unknown.

The `skills` of each match result is the union of the job's own skills and the
skills the worker associated with the job (mentions in an explicit requirement
context, never a bare mention), deduplicated by normalized name and in a
deterministic case-insensitive order. The stored job is not changed and the
response shape is unchanged.

## Alternatives considered

- **Keep labels only.** Safest, but leaves most jobs without senioridade or
  modality, which also removes those dimensions from the compatibility score.
- **Read free prose or the whole description** for these words. Rejected: it
  cannot separate a requirement ("pessoa sênior") from a statement about the
  vacancy, and it is the kind of inference the project avoids.
- **Persist extracted skills into `Job.skills`.** Rejected: extraction state is
  stored apart from the canonical job and changing `Job.skills` would change the
  content hash and re-run extraction.

## Rationale and consequences

Ordering by evidence strength keeps explicit data authoritative: a label or a
body field is never overridden by the title. Requiring one distinct value keeps
ambiguity unknown. The title rule is the weakest evidence; titles such as
`Pleno/Sênior` or `[Remoto ou Presencial]` stay unknown, but a label that is
itself ambiguous (`Remoto/presencial`) is not evidence at all, so a title
`[Remoto]` can still fill the field. Work arrangement remains descriptive and
never drives geographic eligibility.

The mapped fields are part of the content hash, so stored jobs are re-queued for
extraction and embedding. Showing extracted skills means `skills` in a result is
no longer only source-supplied data; clients should treat it as the union.
