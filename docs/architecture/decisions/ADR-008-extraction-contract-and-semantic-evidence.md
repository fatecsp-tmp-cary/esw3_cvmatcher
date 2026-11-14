# ADR-008: GLiNER extraction, fixed integration contract and semantic evidence

- **Status:** Accepted
- **Date:** 2026-11-11
- **Authority:** User decision to document GLiNER extraction, an immutable Sistema
  Currículo contract and experience/education semantic scoring; subsequent
  clarification selects the three highest-matching experiences and best education.

## Context

Job descriptions contain useful fields and requirements beyond structured source
metadata. The sibling `../gline` prototype provides local examples of span
extraction, bounded overlapping chunks, confidence thresholds, contextual
requirement classification and manual evaluation. It is an implementation
reference, not a runtime dependency or production validation dataset.

A single flattened candidate embedding obscures individual experience and
education relevance. Internal extraction/scoring improvements must preserve the
agreed Sistema Currículo integration boundary.

## Decision

Use a local GLiNER extraction stage for job text as specified in the
extraction strategy (planned in #170: `../../data/job-field-extraction.md`). Normalize extracted
spans through shared aliases/taxonomy and validate them before canonical mapping.
Do not infer mandatory status from an entity label or model confidence alone.
Source identity, availability and explicit structured metadata remain authoritative;
uncertain or conflicting extraction must not silently overwrite them.

The existing Sistema Currículo public contract is immutable: preserve field
names/types, requiredness, accepted values, validation limits, date/null semantics,
query parameters, response shape and privacy-safe error behavior. Internal
adapters, models and scoring cannot require caller changes. Any future incompatible
contract must be separately versioned and explicitly approved; never silently
modify the existing contract. See the [contract authority](../../../specs/feature-001-mvp/acceptance.md#resolved-api-contract).

For each candidate-job pair, semantically evaluate every experience separately,
using its title and description. Evaluate every education entry separately from
its existing course/degree title and available descriptive fields. The public
education DTO has no description field: do not invent or require one. Preserve
all source sections in transient normalization.

Select the three experiences with the highest semantic similarity to that job,
not simply the three most recent. Break equal similarity by recency, then a
stable input-position tie-break. Give more recent selected experiences greater
aggregation weight, using existing start/end dates; ongoing experience sorts
before completed experience, then end date and start date descending. Equal
recency receives equal weight. Use the highest semantic education score; do not
average unrelated education entries into it.

Normalize each per-entry similarity to [0,100] using a versioned calibration.
Experience score E is the weighted mean of the selected (up to three) scores;
education score A is the maximum education score. Semantic score is a normalized
weighted combination of E and A, with positive configured weights. Normalize over
available sections; a missing section is not invented evidence. No experience
and no education yields zero evidence for this component. Exact recency weights,
experience/education mixing coefficients and similarity calibration require
regression evaluation before implementation is considered complete.

Retain the final textual/semantic/structured blend currently specified by the
feature; this decision changes how its semantic component is computed. Other
candidate sections remain available to textual/structured matching. Version the
algorithm and model/configuration; identical normalized inputs and versions must
produce identical ranking. Candidate embeddings remain request-scoped.

## Alternatives

Dictionary-only extraction remains useful for aliases and validation but does
not satisfy the selected GLiNER extraction strategy. Unvalidated model output
would turn uncertain evidence into authoritative requirements. A changed public
DTO would burden the integration caller. A single flattened CV embedding, top
three by recency, or an average of all education entries would not implement the
requested per-entry selection.

## Consequences

Extraction needs a pinned model/configuration, offline fixtures, quality/runtime
measurements and bounded background execution. Extraction metadata belongs in
separate supporting structures, not extra canonical Job or public API fields.
Scoring requires per-entry evaluation and additional regression coverage. These
are accepted requirements, not claims of implemented behavior. No major runtime
architecture change is implemented by this documentation change.
