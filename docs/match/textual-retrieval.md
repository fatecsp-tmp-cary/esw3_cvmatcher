# Portuguese textual retrieval

Authority: [ADR-004](../architecture/decisions/ADR-004-portuguese-full-text-search.md),
[ADR-005](../architecture/decisions/ADR-005-weighted-any-term-fts.md), the
[MVP spec](../../specs/feature-001-mvp/spec.md) and
[architectural invariants](../architecture/invariants.md). Implementation:
`src/indexing/textual.py` and `src/matching/textual.py`.

`portuguese-weighted-any-term-v2` uses explicit `pg_catalog.portuguese`
configuration and PostgreSQL standard weights:

| Weight | Evidence |
| --- | --- |
| A (1.0) | Title and skills |
| B (0.4) | Company, keywords and normalized requirement text |
| D (0.1) | Description and location |

`job_search_document()` builds immutable `coalesce` and text concatenation
expressions. Skills/keywords arrays and location objects use PostgreSQL JSON
text rendering, including object keys and scalar values, as accepted in ADR-005.
There is no string-only JSON filter. `requirement_search_document(value=None)`
uses normalized `JobRequirement.text` at weight B; an explicit SQL text expression
supports migration tables/aliases. Indexes and retrieval must use these same
helpers. No canonical Job field or candidate persistence is added.

Job fields and requirement rows are searched independently, then combined per
job: raw job rank plus the maximum matching requirement-row rank. Repeated
requirement rows cannot multiply rank. Optional `requirements=` on
`job_search_document`, `textual_statement` and `retrieve_textual` accepts a
job-only normalized SQL expression rendered as text at weight B. Integrators
must avoid passing the same evidence there and through requirement rows, and
must keep any custom indexed expression identical to retrieval.

`any_term_query()` binds plain text and uses PostgreSQL `plainto_tsquery` to
stem and quote lexemes. Replacing its conjunctions with OR and casting directly
to TSQUERY avoids stemming parsed lexemes twice. Operators/quotes supplied by
users remain ordinary text. Empty/stopword-only queries match nothing. English
input is accepted, but Portuguese stemming does not provide English stemming
or guarantee accent-insensitive matching.

Every retrieval entry point requires an explicit SQL predicate proving current
successful extraction to return jobs. Omitted `readiness` becomes SQL false in
both job and requirement branches, including the legacy wrapper. Integrators
must check current content hash and extraction configuration; pending, failed
or obsolete extraction remains withheld. An explicit true predicate appears only
in focused FTS fixtures. Only ACTIVE jobs pass. Location is textual evidence,
never geographic eligibility.

`textual_statement()` returns `Select(Job, textual_score)` and supports appended
Job pool predicates. `retrieve_textual()` returns `(Job, float)` tuples for the
staged pipeline. Their score is `100*r/(1+r)` applied **after** combining raw
rank, giving a bounded `[0,100]` component. Legacy `search_active_jobs()` returns
frozen `TextualMatch(job, score)` objects with **raw**, unbounded PostgreSQL rank.
Both legacy names remain exported from `src.matching`. Neither score represents
final compatibility or employment probability. Ties use publication date descending
with nulls last, then platform, source ID and persisted ID ascending. Sources
remain independent. Pipeline retrieval limits are positive internal integers;
the legacy result limit remains 1–500. Query text has no extra length cap.

The candidate query includes experience title/description, education course/level,
project title/description/technologies, competencies and languages. It excludes
UUIDs/dates. Candidate text and results remain request-scoped and must not be
logged or persisted.

Offline tests cover SQL construction, API shape, safe binding and fail-closed
predicates. PostgreSQL regressions cover field weights, JSON text, requirement
rank combination, readiness, publication ties and immutable expression indexing;
the [PR #172 review](../reports/2026-11-14-pr172-review.md) records current
PostgreSQL verification after merging predecessor fixes. Migrated index/ORM
expression parity is tested. The request-scoped matching pipeline now combines
these scores with semantic and structured evidence, and fingerprints retrieval
and scoring policies in its algorithm version. It rechecks considered jobs for
current textual or semantic evidence before returning them. API composition
remains planned in #175; this is not production performance evidence.

The current JSON serializer escapes non-ASCII characters. The specific `Café`
and `Paraná` regressions pass because Portuguese queries stem to `caf` and
`paran`, which also occur before the escaped suffixes in their indexed JSON text.
Keep these regressions, but do not infer general accent-insensitive retrieval;
the approved broader projection remains future work under ADR-022.

## Accepted next retrieval policy (not implemented)

[ADR-022](../architecture/decisions/ADR-022-bilingual-ascii-search-and-fuzzy-fallback.md)
accepts a separate lowercase ASCII search projection, PT/EN stemming and fuzzy
fill-only fallback when ordinary combined retrieval cannot fill the request.
Canonical Unicode and extraction offsets remain unchanged. Technical projection,
threshold and index alternatives require measured comparison under #147/#159;
existing Portuguese queries/indexes above describe the current implementation.
