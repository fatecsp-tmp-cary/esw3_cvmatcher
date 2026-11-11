# Portuguese textual retrieval

Authority: the [MVP spec](../../specs/feature-001-mvp/spec.md) and
[architectural invariants](../architecture/invariants.md). Implementation:
`src/indexing/textual.py` and `src/matching/textual.py`.

`portuguese-weighted-any-term-v1` builds a PostgreSQL search vector with explicit
`pg_catalog.portuguese` configuration and these weights:

| Weight | Job evidence |
| --- | --- |
| A | Title |
| B | Skills and validated requirement text supplied from supporting metadata |
| C | Company |
| D | Description and location values |

JSON fields use `jsonb_to_tsvector` with the string-only filter. Object keys,
numbers and booleans are excluded; Unicode strings are processed directly by
PostgreSQL. Requirement input must contain normalized job requirement text,
not an entire extraction-evidence object with incidental string metadata. Until
the caller supplies this SQL JSON expression, the requirement section is empty.
The helper adds no canonical Job fields or candidate persistence.

The same `job_search_document()` expression can be used in a GIN expression index.
Its explicit configuration avoids session-dependent tokenization and satisfies
PostgreSQL's immutable-index requirement. An actual index creation/drop is
covered by the PostgreSQL tests. Schema integration belongs to the orchestrator;
this change does not install an index or claim indexed production performance.
When requirements come from separate supporting state, integration must select
an indexable document representation and keep retrieval/index expressions equal.

`textual_statement()` accepts bound plain query text. PostgreSQL first uses
`plainto_tsquery` to tokenize, stem and safely quote lexemes; replacing its generated
conjunctions with disjunctions yields any-term retrieval. Submitted query operators
are never interpolated into SQL or used as raw tsquery syntax. Empty and
stopword-only queries match no jobs. English input is accepted, but the Portuguese
configuration provides Portuguese stemming; cross-language quality and accent
comparisons remain evaluation work.

Only ACTIVE jobs pass. Callers must also supply a SQL predicate proving current
successful extraction; omitted readiness becomes SQL false. Integrators must use
current content hash and extraction configuration when constructing that predicate.
A caller-provided true predicate is used only by isolated retrieval tests and is
not extraction proof. Pending, failed or obsolete extraction must remain withheld.
Location participates as descriptive textual evidence without geographic filtering.

Rank uses `ts_rank_cd` normalization 32, multiplied by 100, giving a bounded
`[0,100]` textual component. This is a deterministic monotonic rank normalization,
not semantic calibration, final compatibility or employment probability. Ties
use platform, source job ID, then persisted ID; jobs from different sources stay
independent. Retrieval limits are internal positive integers and impose no new
public input caps.

The candidate text projection includes each experience title/description,
education course/level, project title/description/technologies, competency text,
and language name/level. It excludes UUIDs and dates. Candidate projection, bound
query text and results remain request-scoped and must not be logged or persisted.
Production API wiring, extraction integration, migration/index installation,
semantic retrieval and final ranking remain separate work.
