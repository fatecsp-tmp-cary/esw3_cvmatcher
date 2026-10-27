# MVP implementation plan

This is the proposed sequence, not a claim that work is complete. Reorder only
with an explicit rationale and synchronized task/document updates.

1. Verify APiBR pagination and scan behavior, documenting whether a completed
   scan proves a complete covered set. Until established, do not use absence to
   mark jobs `STALE`; implement only lifecycle behavior supported by explicit
   source evidence.
2. Core domain: Job, DB schema/migrations, lifecycle, hashing. Enforce unique
   `(platform, source_job_id)` identity and reject missing or blank IDs.
3. Candidate validation, normalization, and taxonomy.
4. Ingestion interface, polling modes, APiBR source, normalization, source runs,
   and upsert.
5. Lifecycle timestamps, stale/expired/reactivation, failure protection,
   snapshot semantics, explicit expiration. Absence-based `STALE` transitions
   depend on the verification outcome in step 1.
6. Additional API/ATS adapters and optional web adapters; retain no-dedup rule.
7. PostgreSQL FTS, local embeddings, pgvector, and regeneration.
8. Filters, textual/semantic retrieval, structured scoring, ranking,
   normalization, and versioning; no geographic filtering.
9. Matches API, health, OpenAPI, errors, production authentication.
10. Quality suite, regression dataset, model-version migration, no-dedup and
   no-geographic-filtering regressions.
11. Docker/production configuration, secrets, backups, deployment, scheduling,
   and monitoring.

Resolve the dependent questions in [acceptance](acceptance.md) before building
the relevant source/lifecycle, schema, API-contract, or taxonomy behavior. The
APiBR verification in step 1 addresses clarification 1; record its evidence and
outcome in the source-selection record and update the acceptance criteria and
ADR if the decision changes the architecture.
