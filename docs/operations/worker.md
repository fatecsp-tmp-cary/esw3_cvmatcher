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
Register it with `python -m src.worker.sources register apibr`; see
[deployment](deployment.md). Other enabled names require explicit adapter
registration; unknown names record
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

### Daily schedule and poll on start

Two optional worker settings change when sources are polled; without them the
interval behavior above is unchanged:

- `CVMATCHER_SOURCE_DAILY_AT` (`HH:MM`, 24-hour) with `CVMATCHER_SOURCE_TIMEZONE`
  (IANA name, default `UTC`): after each poll, `next_run_at` is the next
  occurrence of that local time instead of completion plus `polling_interval`.
- `CVMATCHER_SOURCE_POLL_ON_START=1`: the first cycle of the long-running worker
  polls every enabled source even when it is not due yet. A source whose
  `last_run_at` is newer than ten minutes is skipped, so a restart loop cannot
  repeatedly request the source. `python -m src.worker --once` never forces a poll.

Invalid values fail worker startup with the fixed `worker_configuration_unavailable`
category. The source lock still prevents overlapping polls. The production
Compose file sets poll on start and `08:00` `America/Sao_Paulo`; override the
three variables in the private environment file to change them. For APiBR the
poll is also the availability check under
[ADR-014](../architecture/decisions/ADR-014-apibr-listing-presence-is-open-evidence.md).

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

`python -m src.worker --once` runs one bounded production cycle.
`python -m src.worker --retry-extraction JOB_ID` explicitly resets extraction
work for that persisted numeric job ID using the configured extraction version.
This command neither receives nor stores a curriculum and does not change job
availability. The operations are mutually exclusive. The default command runs a
loop with a five-second delay; SIGINT/SIGTERM request a stop after the active cycle
and interrupt idle waiting. They do not forcibly terminate in-flight model/HTTP
work. Injected source transport retains its own bounded page request policy.

The entrypoint imports `src.worker.bootstrap.create_default_worker()`. It uses
`DATABASE_URL` for PostgreSQL, requires `CVMATCHER_EXTRACTION_DIRECTORY` to point
to the prepared pinned GLiNER directory, and passes `CVMATCHER_EMBEDDING_CACHE`
to the offline embedding encoder. Extraction uses `EXTRACTION_VERSION` from the
pinned policy. Missing/invalid extraction artifacts fail startup with a fixed
safe category. Embedding loading is lazy; a missing cache fails processing using
the service's bounded retry policy. API readiness separately validates its model.

Embedding maintenance enqueues at most 100 non-expired jobs with successful,
current extraction and missing/outdated embedding provenance, then processes at
most 100 claims. Current FAILED rows are excluded from maintenance enqueueing;
no daily reset or automatic explicit retry occurs. Both model services retain
their three-attempt ceilings and backoff. Unit tests patch model constructors
and session boundaries; serving uses the actual local inference classes.

See [deployment procedures](deployment.md) for Compose setup and recovery.

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
