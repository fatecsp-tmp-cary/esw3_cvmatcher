# Local background worker

`SourceScheduler` and `BackgroundWorker` implement bounded, injectable local
processing using PostgreSQL as the only coordination/state store. See the
[MVP source and worker requirements](../../specs/feature-001-mvp/spec.md) and
[extraction policy](../data/job-field-extraction.md). This adds no candidate
persistence, source, migration, geographic filter or absence-based expiration.

## Scheduling and coordination

`SourceScheduler(engine, sessions, pollers=...)` uses a new independent SQLAlchemy
Session from `sessions()` for each poll. A poller receives `(session, source_id)`
and returns an object with `status` equal to `SUCCEEDED`, `PARTIAL` or `FAILED`.
The default poller maps the case-folded source name `apibr` to `ingest_apibr`.
Other enabled names require explicit adapter registration; unknown names record
`unsupported_source` without invoking another source or making hidden requests.

Only enabled sources with no `next_run_at` or a due timestamp are considered,
ordered by due time and stable source ID. Each cycle considers at most ten
sources by default. A dedicated AUTOCOMMIT connection holds a PostgreSQL
session advisory lock for each poll; a second worker skips a locked source.
This connection is independent of the ingestion Session, so ingestion commits do
not release coordination. The source is rechecked after acquiring the lock.
Unlock runs in `finally`; uncertain acquisition/unlock discards the physical
connection rather than returning a potentially locked session to the pool.

A configured positive integer `polling_interval` is measured in seconds. Missing,
zero or negative intervals use a conservative 3,600-second default. The scheduler
records `last_run_at` and reserves `next_run_at` before polling. After completion,
it schedules the next run relative to completion time; only `SUCCEEDED` advances
`last_success_at`. Partial/failed polls preserve the previous success and record
fixed safe error categories. Existing ingestion still owns per-run evidence and
its rollback/PARTIAL semantics. Logs contain numeric source IDs and fixed status
values, never source/job text or exception messages.

## Processing and operations

`BackgroundWorker(scheduler, sessions, extraction_worker, config_version, ...)`
runs one bounded cycle through `run_once()`: due source polls, an injected
expiration callback, extraction enqueueing, at most 100 extraction claims, then
an injected embedding-maintenance callback. Callbacks receive no arguments;
production integration supplies closures with the required local models/sessions.
Stage failures emit fixed categories and permit later independent stages to run.
The CLI returns failure for a failed stage in `--once` mode.

Enqueueing selects non-expired stored jobs with nonempty content hashes and
missing or outdated extraction content/configuration. It never resets current
FAILED, RUNNING, PENDING or SUCCEEDED extraction state. The extraction service
retains its three-attempt ceiling, backoff and explicit-retry requirement.
No availability transition is inferred from extraction or polling failure.

`python -m src.worker --once` runs one cycle after production factory wiring.
`python -m src.worker --retry-extraction JOB_ID` explicitly resets extraction
work for that persisted numeric job ID using the configured extraction version.
This command neither receives nor stores a curriculum and does not change job
availability. The operations are mutually exclusive. The default command runs a
loop with a five-second delay; SIGINT/SIGTERM request a stop after the active cycle
and interrupt idle waiting. They do not forcibly terminate in-flight model/HTTP
work. Injected source transport retains its own bounded page request policy.

The entrypoint's `create_default_worker()` intentionally fails safely until
production integration supplies the pinned extractor, model/config versions,
database engine, embedding callback and reliable source-expiration callback.
Unit tests can inject `main(..., worker_factory=...)`; do not replace local model
inference with a fake extractor in production. This implementation does not
claim that model/bootstrap wiring or complete Compose deployment is ready.

For model/config changes in pre-production, stop workers/API, update the pinned
configuration, reprocess jobs, verify matching readiness and restart. Missing or
stale extraction remains withheld throughout. Keep FAILED current work stopped
until an explicit retry; do not introduce a daily retry reset. Stop/reprocess/
restart follows [ADR-010](../architecture/decisions/ADR-010-preproduction-and-minute-rate-limit.md).
Persist PostgreSQL/model cache volumes across restarts; never remove volumes as
part of ordinary worker shutdown.

The expiration callback must use only reliable `source_expires_at` timestamps.
No approved age/missing-snapshot thresholds exist here. An unproven/partial scan
cannot mark absent jobs stale or expired. No callback implements geographic
eligibility. Live source access, model inference/quality, and complete deployment
checks remain separate acceptance work; deterministic tests use synthetic jobs
and injected local components only.
