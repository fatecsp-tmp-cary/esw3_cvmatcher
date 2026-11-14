# ADR-021: Exact-evidence mandatory coverage remains score-only

- **Status:** Accepted
- **Date:** 2026-11-14
- **Authority:** User interview following the extraction correction and branch decision audit.
- **Supersedes:** No evaluation sample minimum or final blend; this adds an accepted per-job score-only coverage policy.
- **Implementation status:** Policy recorded; implementation and verification remain pending unless separately evidenced in feature tasks.

## Context

The evaluation sample-size interview elicited a per-job coverage rule, not a
minimum validation corpus. Three correct English regression predictions do not
establish exclusion reliability. The user retains score-only processing.

## Decision

Let N be the number of explicit REQUIRED concepts after the accepted strongest-
occurrence consolidation. For N=1 or 2, require N matches. For N>=3, require
max(3, ceil(0.70*N)) matches. Examples: 1→1, 2→2, 3→3, 4→3, 5→4, 10→7.
Only exact candidate matches and explicitly approved aliases satisfy a requirement.
Unknown, negated, conflicting or fuzzy evidence cannot satisfy the count. PREFERRED
and NICE_TO_HAVE do not enter N. Preserve the evidence flags so score associations
are not mistaken for exact satisfaction. For N=0 there is no mandatory coverage
threshold to fail; retain existing missing-evidence/empty-candidate semantics.

This is score-only coverage information. It cannot change eligibility, remove
results, enable exclusions, change the public DTO or silently introduce a new
final-score weight. Numerical reviewed mandatory precision/recall gates remain
95%/80%, separate from the per-job 70% rule. Additional minimum gold/predicted
mandatory mention counts for future exclusion approval remain deferred.

## Alternatives and rationale

Three matches alone does not scale with job requirements. Requiring three plus
70% of the remainder was offered; the user selected a floor of three and 70% of
the total instead. Counting preferred/optional evidence or approximate aliases
would conflate weak supporting evidence with mandatory satisfaction.

## Consequences

Issue #120 must implement/version the coverage calculation and regress rounding,
0/1/2/3/4/5/10 requirements, consolidation, exact aliases and blocked evidence.
Keep the existing final blend and exclusions disabled. New independent held-out
review is still required for acceptance; this per-job rule does not replace it.
Implementation and any integration into a numerical score remain unverified.
