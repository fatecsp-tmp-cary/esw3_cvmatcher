# MVP implementation plan

This is the proposed sequence, not a claim that work is complete. Reorder only
with an explicit rationale and synchronized task/document updates.

1. Core domain: Job, DB schema/migrations, lifecycle, hashing.
2. Candidate validation, normalization, and taxonomy.
3. Ingestion interface, polling modes, APiBR source, normalization, source runs,
   and upsert.
4. Lifecycle timestamps, stale/expired/reactivation, failure protection,
   snapshot semantics, explicit expiration.
5. Additional API/ATS adapters and optional web adapters; retain no-dedup rule.
6. PostgreSQL FTS, local embeddings, pgvector, and regeneration.
7. Filters, textual/semantic retrieval, structured scoring, ranking,
   normalization, and versioning; no geographic filtering.
8. Matches API, health, OpenAPI, errors, production authentication.
9. Quality suite, regression dataset, model-version migration, no-dedup and
   no-geographic-filtering regressions.
10. Docker/production configuration, secrets, backups, deployment, scheduling,
    and monitoring.

Resolve the dependent questions in [acceptance](acceptance.md) before building
the relevant source/lifecycle, schema, API-contract, or taxonomy behavior.
