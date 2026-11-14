# ADR-018: Clause-local extraction and approximate score evidence

- **Status:** Accepted
- **Date:** 2026-11-14
- **Authority:** User interview for issue #116 / PR #170 and evaluation follow-up.
- **Supersedes:** Supporting extraction policy's global conflict-to-null rule and
  earlier annotation conventions that excluded negated mentions. ADR-008 API,
  privacy and canonical Job boundaries and ADR-012 numerical gates remain in force.

## Context

The reviewed failed evaluation and causal analysis found line-wide cue leakage,
background predictions projected as requirements, boundary differences, missing
credential/language labels and inconsistent class meanings. The sibling
`../gline/extract_requirements.py` is a reference, not a runtime dependency:
its section-over-local override and preference-first precedence are unsuitable.
The old held-out set has informed diagnosis and cannot remain independent after
this change. Original labels, reports, predictions and errors must be preserved.

## Decision

1. Classify explicit clauses independently within sentences. Shared lists retain
   their predicate. Section context is fallback only; a local cue or negation wins.
   Multiple strengths governing one mention use the strongest, in order
   `null < NICE_TO_HAVE < PREFERRED < REQUIRED`.
2. Negated mentions, including PT/EN equivalents of not required/not necessary,
   remain detected null evidence. Hedges such as maybe useful/could be needed/
   would be a plus/talvez útil/pode ser necessário are NICE_TO_HAVE. Unknown or
   genuinely ambiguous evidence stays null. Detection does not establish strength.
3. `diferencial` is PREFERRED. Bonus, plus, optional and nice to have are
   NICE_TO_HAVE. Repeated concepts produce one selected requirement at the
   strongest occurrence (earliest offset for equal strength). Retain every raw
   detection and its occurrence strength. Conflicting strengths or affirmative
   and negated occurrences retain conflict flags and never authorize exclusions.
4. Use the smallest meaningful entity, trimming grammatical wrappers while
   retaining multiword names, credential classes and experience quantities.
   Offsets are exact zero-based Unicode code-point offsets with exclusive end
   in the original cleaned text. Never locate spans in normalized/fuzzy text.
5. Requirement/qualification/preference/bonus headings activate requirement
   scope. Benefits, company background, responsibilities, application instructions
   and unrelated headings terminate it. Ignore explicit background/promotional
   context; repetition alone must not remove a requirement. Without recognized
   requirements sections, scan the entire description using local cues. A malformed
   heading cannot supply mandatory strength. Preserve full chunk coverage.
6. Add distinct internal professional credential, professional license, language
   and certification labels alongside education, work experience and technology
   labels. The versioned, project-maintained alias vocabulary is authoritative
   for exact equivalence. Preserve accepted CEFR/language rules. No external
   vocabulary or language-framework equivalence is invented.
7. Exact names/aliases win. For unknown terms, allow at most one insertion,
   deletion, substitution or adjacent transposition, with both terms at least
   five characters, identical punctuation/word-boundary structure, and exactly
   one closest canonical concept. Apply to job entities and transient candidate
   matching. Preserve originals and approximate-match provenance. This is
   score-only supporting evidence, not canonical equivalence, mandatory
   satisfaction, permanent alias creation or exclusion evidence. Short names
   (C/R/Go/PHP), punctuation distinctions and known different names stay distinct.
8. Semantic similarity supports relevance, not automatic canonical merging.
   The approved pinned-E5 diagnostic could not separate C/C#, C/R and
   Java/JavaScript from Ruby/Rails and PHP/WordPress with one scalar threshold.
   Related technologies are not aliases. No PostgreSQL extension/new retrieval
   architecture is introduced; retain accepted FTS behavior.
9. Empty candidates retain zero semantic evidence/no matches and are irrelevant
   in role evaluation. A job without explicit requirements is judged by available
   candidate-to-role evidence, never relevant by default. These cases remain in
   accuracy/AUC with explicit positive/negative support checks.
10. Reuse reviewed calibration cases; update versioned annotation copies solely
    according to these decisions, with a case-level change record. User-authorized
    policy adjudication is distinct from a new independent human annotation.
    Update the old held-out packet similarly but designate it regression/development
    evidence. Do not claim a new independent acceptance test. After freezing
    extraction/configuration, calibration parameters and cutoff, future acceptance
    still requires a fresh independently reviewed held-out set. Never tune on old
    held-out outcomes; retain failed runs and errors.
11. Keep all new exclusions disabled, score-only, and release approval false.
    The user chose score-only instead of selecting relaxed numerical gates.
    Retain ADR-012 targets per language: span precision/recall 90%/80%, mandatory
    precision/recall 95%/80%, semantic AUC 0.90, role accuracy 80%, complete coverage
    and defined metrics with positive support. Additional minimum mandatory-mention
    counts remain pending for future exclusion approval; they do not block a
    score-only correction. No merge or deployment is authorized.

## Alternatives and rationale

Whole-line classification lets unrelated predicates/negation leak between
sentences. Preference-first classification discards explicit stronger evidence;
global null consolidation loses the user's requested strongest interpretation.
Silently relabeling to model outputs, removing difficult cases, or tuning to the
old held-out set would conceal failures. Semantic-only equivalence fails the
approved collision probe. Unrestricted fuzzy matching conflates short or
punctuation-sensitive names; bounded approximation retains its uncertainty.

## Consequences

Version context/span/classification/taxonomy policy with extraction artifacts;
unchanged jobs require re-extraction and downstream invalidation under the existing
stop/reprocess/restart policy. Supporting job evidence may retain selection,
negation, conflict and approximation metadata; canonical Job and public API stay
unchanged. Candidate data and embeddings remain request-scoped and never logged
or persisted. Ordinary CI uses deterministic injected models; actual offline
calibration is separate evidence. Passing regressions is not release approval.

## Identifier reconciliation (2026-11-14)

This is the unchanged accepted extraction policy formerly assigned ADR-014 on
the extraction branch. Later source branches had already assigned ADR-014 to
APiBR listing availability. ADR-018 is the unique current extraction identifier;
ADR-014 remains APiBR availability. This renumbering changes no extraction rule,
runtime version, calibration parameter or release gate. The original path is a
historical redirect. Frozen evaluation identifiers and reports retain their
original bytes; old extraction-specific ADR-014 identifiers refer to this record.
