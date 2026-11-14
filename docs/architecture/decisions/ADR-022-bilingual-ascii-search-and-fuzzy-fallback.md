# ADR-022: Bilingual ASCII search projection and bounded fuzzy fallback

- **Status:** Accepted
- **Date:** 2026-11-14
- **Authority:** User interview following the extraction correction and branch decision audit.
- **Supersedes:** ADR-004/005 Portuguese-only query policy for the future implementation, and canonical-ASCII replacement as an alternative; existing weights/privacy/source invariants remain.
- **Implementation status:** Policy recorded; implementation and verification remain pending unless separately evidenced in feature tasks.

## Context

Portuguese-only FTS and exact words miss English forms, accents and typing errors.
The approved extraction spelling policy does not define general document retrieval.
Replacing canonical Unicode text would break display and exact extraction offsets.

## Decision

Maintain a separate lower-case ASCII search/matching representation for job and
request-scoped candidate text. Transliterate accents (programação → programacao);
preserve meaningful ASCII punctuation in C#, C++ and Node.js. Characters without
a supported transliteration become separators, never silently joining words.
Keep original cleaned Unicode for canonical/display fields and extraction offsets.
Never use offsets into the search projection as original text offsets.

Search with both Portuguese and English stemming. Use fuzzy document retrieval
only when ordinary combined textual and semantic retrieval yields fewer ready
jobs than the requested limit. Fuzzy-only results may fill the remaining positions,
with ordinary results first and deterministic ranking/ties within the fallback.
Retain the active-before-inactive group priority wherever the later inactive-result
policy applies: use ordinary then fuzzy results within each group, never place an
inactive result ahead of an active result. Preserve source-specific job identity.

Fuzzy retrieval does not establish canonical equivalence, mandatory satisfaction
or exclusion. The existing minimum-five-character/one-edit skill policy remains
separate. No new percentage cutoff, fuzzy blend weight, database extension or
index layout is approved by this behavioral decision.

## Alternatives and rationale

Keeping Portuguese-only literal retrieval misses supported English/accent variants.
Lowercasing/transliterating canonical text would lose evidence. Unrestricted fuzzy
retrieval can swamp exact results; a bounded fill-only fallback preserves ordinary
results. Compare implementation alternatives and measured precision/latency before
selecting technical thresholds or rebuilding indexes.

## Consequences

Issues #147/#159 and downstream retrieval must compare PT/EN, accented/ASCII,
punctuation-sensitive names, typo collisions, duplicate retrieval, readiness,
active/inactive priority, deterministic limits and empty results. Specify the
projection/transliteration algorithm and its unsupported-character handling before
implementation; version representations/queries/indexes and measure rebuild impact.
Candidate projections stay transient and are never persisted or logged. No code,
index migration or production rollout is implemented by this ADR.
