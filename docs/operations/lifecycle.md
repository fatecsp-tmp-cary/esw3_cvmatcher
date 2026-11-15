# Evidence-based expiration

`src.lifecycle.expiration.expire_source_timestamps(session, now=...)` expires
stored jobs only when their normalized, reliable `source_expires_at` is due.
The caller owns the transaction. Its clock must be a timezone-aware datetime.
Records remain stored, and repeated execution is idempotent. EXPIRED is terminal.
The sweep preserves first/last observation and verification timestamps.

The normalized expiry field is an adapter precondition: populate it only from a
validated, explicit, reliable upstream expiry field. Never substitute observation,
publication or fallback dates. APiBR supplies no supported expiry field and its
normalizer always emits null. Upserts reject non-datetime and timezone-ambiguous
expiry values; this validates representation, not a source's truthfulness. Source
reliability must be established before implementing an adapter mapping; no new
source expiry mapping or provenance metadata is introduced here.

Before changing rows, the sweep acquires all 256 bounded ingestion advisory
stripes in ascending order, using the same namespace as upserts. This prevents
stale reactivation from overwriting terminal expiration and avoids opposite row
order deadlocks between multi-record ingestion and sweeps. It serializes other
identity writers during the sweep's database transaction; commit or rollback
promptly, without remote I/O while locks are held. Run the sweep as the first
identity-lock operation in its transaction, or pre-acquire the complete stripe
set: expanding a previously held subset can invert acquisition order. A partial index on nonterminal
rows with a source expiry supports the due-time predicate while historical expired
rows remain retained. Migration b1e007 adds the index.

Polling failures, old `last_seen_at`, and missing jobs in incomplete APiBR scans
are never expiration evidence. Under
[ADR-015](../architecture/decisions/ADR-015-qualifying-snapshot-absence-marks-stale.md),
`ACTIVE` jobs of a source absent from one qualifying SNAPSHOT poll become `STALE`,
and a later poll that lists them again reactivates them. `SourceRun.jobs_absent`
and `jobs_marked_stale` record the counts. The `STALE→EXPIRED` policy is now three qualifying absence snapshots with no age
trigger (ADR-020); counters and implementation remain pending #145. Extraction/embedding state
is independent: failures withhold matching readiness without changing availability.

For integration verification, provide a dedicated PostgreSQL/pgvector database
through `TEST_DATABASE_URL` and run:

```sh
pytest tests/integration/lifecycle tests/integration/ingestion/test_source_upsert_concurrency.py
```

The repository's
`tests/conftest.py` connects to that database and applies migrations; it does not
provision a disposable database container.

## Accepted absence expiration threshold (implementation pending)

[ADR-020](../architecture/decisions/ADR-020-three-snapshot-stale-expiration.md)
resolves #145: three qualifying absent snapshots, counting the first STALE transition;
no age threshold. Bad scans do not increment; confirmed rediscovery resets the count.
Current one-snapshot STALE and reliable timestamp expiry remain as implemented;
three-snapshot EXPIRED counters and tests still need implementation.
