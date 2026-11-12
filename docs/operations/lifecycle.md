# Evidence-based expiration

`src.lifecycle.expiration.expire_source_timestamps(session, now=...)` expires
stored jobs only when their normalized, reliable `source_expires_at` is due.
The caller owns the transaction. Its clock must be timezone-aware. Records remain
stored, and repeated execution is idempotent. EXPIRED is terminal.

Polling failures, old `last_seen_at`, and missing jobs in incomplete APiBR scans
are never expiration evidence. STALE age/missing-snapshot policies remain pending
until approved source coverage and thresholds exist. Extraction/embedding state
is independent: failures withhold matching readiness without changing availability.

The scoped test helper probes PostgreSQL over TCP, so its temporary initialization
server on a Unix socket cannot produce a false ready signal. It creates and
removes only its uniquely labelled disposable test container.
