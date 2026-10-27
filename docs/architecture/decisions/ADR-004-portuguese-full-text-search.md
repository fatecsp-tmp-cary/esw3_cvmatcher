# ADR-004: Portuguese PostgreSQL full-text search

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

The MVP ingests Brazilian job postings and accepts Portuguese and English CV
content. PostgreSQL full-text search needs one text-search configuration for
the indexed job representation and candidate queries. The feature specification
requires full-text search across title, company, description, skills,
requirements, and location.

## Decision

Use PostgreSQL's `portuguese` text-search configuration for both GIN index
expressions and query parsing. Search title, company, description, keywords,
skills, location, and normalized requirement text. Retrieve active jobs only.
Location may contribute to textual retrieval but never to geographic
eligibility.

## Alternatives considered

- `simple`: language-neutral tokenization without stemming.
- `english`: English stemming, with weaker treatment of Portuguese.
- Parallel Portuguese and English vectors and query ranking: broader bilingual
  stemming at the cost of additional indexes and more complex ranking.

## Rationale

The user selected Portuguese stemming as the initial priority. The source
dataset is Brazilian, and semantic retrieval is separately deferred until the
model selection in issue #26.

## Consequences

Portuguese terms receive PostgreSQL stemming. English searches may rank less
well because English terms use the Portuguese configuration. Replacing this
configuration requires rebuilding the functional indexes and reviewing ranking
regressions. No canonical `Job` field is added for the search vector.
