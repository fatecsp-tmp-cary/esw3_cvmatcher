# Architectural invariants

- Keep ingestion, normalization, indexing, matching/ranking, persistence, and
  API responsibilities separate. Keep matching independent from ingestion.
- Isolate each source behind a common interface; domain models do not depend on
  source formats. Prefer public APIs/structured sources; scraping is optional.
- PostgreSQL is the only application-state store, including scheduler state and
  worker coordination; no dedicated broker is required.
- Candidate profiles, their embeddings, and match results are request-scoped:
  never persist or log them, including request bodies, errors, traces, telemetry,
  or correlation values containing submitted data.
- Ranking is deterministic for identical normalized inputs, jobs, model/version,
  configuration, and algorithm version.
- Respect source terms, rate limits, robots/access and storage restrictions.
- Canonical `Job` has exactly the fields in [architecture overview](overview.md).
  Its `platform` identifies the upstream job platform. The persistence row may
  additionally carry `source_id` solely as a foreign key to `job_sources`, which
  stores adapter/polling configuration; keep that configuration and `source_id`
  out of canonical job data and API payloads. Put other additional persisted
  data in separate structures.
- Lifecycle status represents availability. Expired jobs remain historical and
  are excluded from active retrieval. Polling failure never changes lifecycle.
- Source-specific jobs remain independent: no cross-source deduplication,
  merging, or same-opportunity detection.
- Regenerate embeddings independently after content or embedding model/version
  changes; model changes do not depend on `content_hash`.
- Location and work mode may be stored, normalized, indexed, and included in
  matching representations, but never drive geographic eligibility.
- No candidate persistence model or candidate database tables.

See [ADRs](decisions/README.md) for decision history and [scope](../product/scope.md)
for explicit exclusions.
