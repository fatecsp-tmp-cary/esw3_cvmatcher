# Single-host production composition

This procedure implements the [MVP deployment contract](../../specs/feature-001-mvp/spec.md)
and preserves the [invariants](../architecture/invariants.md). It is a reference
pre-production configuration, not evidence that release acceptance has passed.
Container startup, real inference, end-to-end matching, restart durability and
backup/restore still require a serialized test on synthetic data. No deployment
or image commands were executed for this change.

## Acceptance scope

The user confirmed local pre-production scope in
[ADR-012](../architecture/decisions/ADR-012-issue-completion-and-evaluation-policy.md).
External HTTPS termination and provider-specific deployment remain separate #150
acceptance. The loopback API must not be treated as an externally secured service.
Historical local offline Compose/recovery measurements are recorded in the
[validation report](../reports/2026-11-12-mvp-validation.md); repeat them when
implementation changes warrant it rather than claiming they cover a new head.

## Operational observations

Inspect `docker compose --project-name cvmatch -f docker-compose.yml -f
docker-compose.production.yml logs api worker` on the configured local host.
Matching emits `matching_request_duration_ms` for the full admitted execution,
`matching_duration_ms` for the pipeline, and the fixed `matching_outcome`
(success, empty, unavailable, budget_exhausted) categories. It never emits
curriculum UUIDs, query text, embeddings or result contents. For a direct local API launch, enable only these fixed-category loggers:

```sh
python - <<'PYLOG'
import logging
import uvicorn
for name in ("src.api.app", "src.matching.pipeline"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
uvicorn.run("src.api.app:app", host="127.0.0.1", port=8000, access_log=False)
PYLOG
```

Use this same selective logging configuration in the configured process launcher
to retain duration/status records without enabling body/access logging. Dependency errors remain privacy-safe.
Worker failures use the documented fixed categories and persisted job-only
attempt/readiness state. The process-local one-request limit and cooperative
30-second deadline are separate from the global PostgreSQL 60/minute quota.
An executing native inference call finishes before the next checkpoint can stop
work. Overload returns generic 503; no extra field or collection cap is imposed.

## Configure and prepare

Use Docker Compose v2 on a host sized for PostgreSQL and two CPU model processes.
The configured memory ceilings total about 6.5 GiB; measure peak model loading
before choosing a host. The 2 GiB development guest is not a deployment sizing
claim. Model preparation needs outbound access and additional disk space.

Supply `POSTGRES_PASSWORD`, optional `POSTGRES_USER`/`POSTGRES_DB` (both default
`cvmatch`), and `DATABASE_URL` through a private local environment file or operator
secret environment. Do not commit them. The URL must use host `postgres`, port
5432 and URL-encoded credentials matching PostgreSQL's settings. Rotating the
variable does not rotate an existing database account. The default PostgreSQL image is pinned to
`pgvector/pgvector@sha256:7d0a41464797aeb9862dfdc0bbf1526b82cfd324cdd8036df19e3545f4a9ccb8`.
Only override `CVMATCHER_POSTGRES_IMAGE` with an independently verified
pgvector/PostgreSQL 17 digest; mutable tags do not satisfy deployment acceptance.

Always use an explicit project name. The following commands use `cvmatch`;
substitute a distinct name for test/recovery projects. Run from the repository:

```sh
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml config --quiet
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml build api
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml --profile prepare run --rm model-init
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml --profile prepare run --rm prepare-extraction
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml --profile prepare run --rm prepare-embeddings
```

The initialization command creates cache directories owned by application UID
10001 in this project's named volume. Preparation runs as that non-root user;
only the explicit preparation services enable network model resolution. Existing
scripts pin revisions and write provenance manifests. Serving is offline and
never downloads models. Retain manifests for recovery and version auditing.
`CVMATCHER_EXTRACTION_DIRECTORY=/models/extraction` is a prepared artifact directory;
`CVMATCHER_EMBEDDING_CACHE=/models/huggingface` is the Hugging Face cache directory.

## Start, verify and stop

```sh
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml up -d postgres migrate worker api
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml ps -a
curl --fail http://127.0.0.1:8000/health
```

No source is configured automatically. After migrations, register the APiBR
source once; the command is idempotent, needs only the database and never loads
a model:

```sh
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml run --rm worker python -m src.worker.sources register apibr --polling-mode SNAPSHOT
```

Use `--polling-mode INCREMENTAL` (the default) to ignore absence, or `--disabled`
to register without polling. `SNAPSHOT` enables the qualifying-snapshot rules of
ADR-013 and ADR-015. Running the command again updates the mode and enabled flag
and preserves scheduling timestamps and run history. Only supported source names
are accepted.

The worker polls enabled sources when it starts and then daily at 08:00
`America/Sao_Paulo`; see the [worker schedule](worker.md#daily-schedule-and-poll-on-start)
for the `CVMATCHER_SOURCE_*` variables that change this.

PostgreSQL must be healthy before migrations run; migration success gates both
application services. `/health` checks database/model readiness; migrations are
not a substitute for model preparation. The API binds only loopback port 8000
(overridable with `CVMATCHER_API_PORT`). PostgreSQL publishes no host port.
Configure a host HTTPS reverse proxy before external exposure. The anonymous API
retains the PostgreSQL-backed global quota of 60 requests per rolling minute,
429 with `Retry-After: 60`, and 503 when admission state is unavailable. CORS is
disabled; callers are server-to-server. Never log submitted curricula or bodies.

Verify synthetic fixture ingestion, extraction and embeddings, then POST the
accepted public fixture to `/matches`; verify determinism, safe failures and
no candidate persistence. This end-to-end smoke check remains unverified here.
Inspect fixed worker error categories and stored job-only processing state when
readiness or results are incomplete. Enable source configurations deliberately;
unknown sources fail safely. No absence-based expiry or daily FAILED reset exists.

```sh
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml stop worker api
docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml down
```

Neither command removes named database/model volumes. Never add `--volumes` or
`-v`. SIGTERM allows the active cycle to finish within the configured grace
period; an interrupted claim recovers under its existing bounded lease policy.

## Updates and explicit recovery

Back up first. Stop API and worker, rebuild the image, explicitly prepare changed
models, rerun `migrate` using `run --rm migrate`, then run bounded worker cycles
using `run --rm worker python -m src.worker --once`. Repeat as needed and check stored
readiness before starting API/worker. Same-version FAILED extraction requires
`run --rm worker python -m src.worker --retry-extraction JOB_ID`. Embedding FAILED
retry requires an operator transaction through the existing embedding `enqueue`
API with `retry=True`; no automatic retry-reset command is provided. Content or
configuration changes enqueue new versions independently. Keep failed artifacts
and logs privacy-safe. Model/config changes use stop/reprocess/restart under
[ADR-010](../architecture/decisions/ADR-010-preproduction-and-minute-rate-limit.md).

## Backup and restore drill

Use an absolute new archive path on a secured filesystem. Backup contains job
and source state, not curricula. Keep model manifests and image/revision records
alongside backups; model caches can be prepared again using their pinned scripts.

```sh
scripts/operations/backup cvmatch /secure/backups/cvmatch-new.dump
```

The script invokes a consistent custom-format `pg_dump` within the explicitly
named project and refuses to overwrite files. A failed command may leave a
partial archive: treat any nonzero exit as an unusable backup. Verify with
`pg_restore --list` in the pinned PostgreSQL image before retention.

For recovery, choose a NEW project and an empty database. Point `DATABASE_URL`
to its configured database; do not start migrations/application services yet.

```sh
docker compose --project-name cvmatch-recovery -f docker-compose.yml -f docker-compose.production.yml up -d --wait postgres
scripts/operations/restore cvmatch-recovery /secure/backups/cvmatch-new.dump --confirm-empty-database
```

Restore refuses initialized databases and uses a single transaction without
DROP/clean options. Prepare the recovery project's model volume, run migrations,
start API/worker and compare synthetic job counts, source state and matching
results. Use a different loopback API port while the original project runs.
Exercise replacement/restart and verify retained jobs/cache before declaring
recovery tested. This drill has not been run in this change. Keep the original
project and volumes until recovery is independently verified.

## Clean-image inference prerequisite

The serving image creates UID/GID10001 with a passwd entry and writable home.
Torch resolves that identity when GLiNER imports its optional compiler support;
a bare numeric USER without a passwd entry fails before extraction. The image
build now imports GLiNER and SentenceTransformers as the real non-root user,
offline and without model weights, to catch this clean-host prerequisite.

## Preserving old extraction artifacts during policy updates

The artifact validator checks the complete extraction policy, including contextual
classification/taxonomy versions. An existing artifact directory is never silently
rewritten for a different policy. For stop/reprocess/restart updates, set
`CVMATCHER_EXTRACTION_DIRECTORY=/models/extraction-POLICY_VERSION` to a new directory
inside the persisted model volume before running `prepare-extraction`; Compose
passes the same configured directory to preparation, worker and API. Its default
remains `/models/extraction`. Retain the old directory for rollback instead of
deleting/overwriting its manifest. The explicit preparation command reuses pinned
local cache files when available; serving remains offline. Reprocess stored jobs
under the new extraction version and confirm readiness before resuming matching.
