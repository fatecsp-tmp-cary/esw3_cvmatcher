# ADR-005: Weighted any-term Portuguese retrieval

- **Status:** Accepted
- **Date:** 2026-11-07
- **Extends:** [ADR-004](ADR-004-portuguese-full-text-search.md)

## Context

Uniform weights let description text dominate, while all-term queries reduce
recall for multi-skill profiles. Functional indexes require immutable expressions
and consistent document/query normalization.

## Decision

Use the same `portuguese` configuration for documents and plain-text queries.
Convert the escaped lexemes from `plainto_tsquery` to an OR query, retaining
stop-word handling and treating user operators/quotes as ordinary text.

Use PostgreSQL's standard weights: A (1.0) for title/skills; B (0.4) for
company/keywords and normalized requirements; D (0.1) for description/location.
Use immutable `coalesce` and concatenation in identical index/query expressions.
Search job fields and requirement rows independently, combine scores per job,
and use publication date, platform, and source ID as deterministic tie-breakers.

Descriptions strip HTML while preserving heading, paragraph, table-cell and
list boundaries; other display text collapses whitespace. Unicode uses NFC.
Keywords/skills arrays and location objects use PostgreSQL JSON text rendering
before tokenization. There is no separate geographic filter or geographic
compatibility component. Normalization keeps `raw` null pending retention rights.

## Alternatives considered

Uniform weights and all-term retrieval are simpler but reduce recall for
multi-skill profiles. Parallel English/Portuguese indexes or an unaccent
dictionary would add configuration and index maintenance beyond this slice.

## Rationale and consequences

The initial retriever favors role/skill evidence while accepting partial term
overlap. Portuguese stemming does not provide English stemming or guarantee
accent-insensitive matching; evaluate those limitations separately. FTS rank
remains an internal raw score, not the final `[0,100]` compatibility score.
Changing index weights/configuration later requires a migration and regression
review. The current functional indexes add no canonical Job field.
