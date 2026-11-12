# Application implementation and verification — 2026-11-11

## Scope and result

The MVP is **not complete**. This change implements lossless request-scoped
curriculum adaptation, direct response-contract regressions, and serialization
of competing source-identity upserts. It adds an isolated rootless PostgreSQL
verification procedure. Public request/response schemas are unchanged.

`normalize_curriculum` retains every section, original validated order/text,
dates, education status/level and free-text proficiency. It excludes the UUID,
accepts empty sections and introduces no extra public caps. Dataclass reprs omit
candidate fields; this does not replace the prohibition on logging candidate data.
The legacy internal profile is explicitly distinguished from the public request.
The production API executor is still unwired and returns 503 by default.

Upserts use a stable identity-keyed PostgreSQL transaction advisory lock and
refresh previously loaded rows after locking. Independent-session tests verify
competing inserts, expiration and stale ORM state. Locks release at transaction
completion; multi-identity batches can still deadlock when lock order differs.
PostgreSQL abort/rollback remains safe, but production batch retry/source
coordination is pending. This is not a claim of complete concurrent scheduling.

## Verification

Working copy: `/home/agent/workspace/esw3_cvmatcher`.
Interpreter: `/home/agent/workspace/cvmatcher-dev/bin/python` (Python 3.12).
Existing environments were unusable because their Python 3.13 symlinks target
an absent `/usr/bin/python`. The user explicitly approved dependency installation.
The working environment uses the currently resolved declared dependencies; no
committed reproducible dependency lock or mypy gate has been delivered.

Commands:

```bash
PYTHON=/home/agent/workspace/cvmatcher-dev/bin/python scripts/testing/postgres.sh --no-cov -q
/home/agent/workspace/cvmatcher-dev/bin/ruff check .
/home/agent/workspace/cvmatcher-dev/bin/ruff format --check .
```

Results: **275 passed**, no skipped tests in the database run; Ruff lint and
format checks passed. Unit/API-only baseline before database setup was 211
passed and 24 skipped. Live external tests remain intentionally excluded.
Coverage was not measured in this run. Pytest reports an existing unset async
fixture-loop-scope deprecation warning.

The disposable helper verifies the per-user rootless daemon, uses the already
available pgvector image, synthetic credentials and a `_test` database, no host
mounts and an ephemeral loopback port. Cleanup checks its unique run label and
removes only that container and its anonymous volumes. Requested resource
limits are 512 MiB, one CPU and 128 processes; effective host cgroup enforcement
was not independently verified. This is an application test helper, not the
full agentic environment management implementation.

## Environment-spec deviations and remaining release gates

The user approved continuing application work on this Ubuntu 24.04 host.
The requested persistent Debian guest, tmux orchestration, durable task database,
protocol/outbox, watchdog/resource dispatch gates, native child inheritance/depth
smoke tests, backup/restore and full environment acceptance are not implemented
or established by this application test run. Available runtime tools did not
include managed-environment status. No Codex version discovery, update, model
subprocess, paid inference, credential changes or global Git configuration
changes were performed. Two native children performed bounded implementation/
review tasks; full three/four-child acceptance was not exercised.

Application release still requires the remaining items in
[the MVP tasks](../../specs/feature-001-mvp/tasks.md), including source evidence,
source interface/retries, taxonomy/extraction, lifecycle policies, FTS,
model/version decisions, semantic calibration and ranking, API wiring/auth,
worker/scheduler, deployment, and release regression coverage. Extraction targets
and scoring coefficients remain unresolved in the governing acceptance document.
Existing uncommitted requirement/ADR changes were preserved.

## Continuation after permissions repair

The user repaired shared-checkout permissions. The 13 previously reviewed files
were synced to `/workspace/esw3_cvmatcher`; subsequent application work is in
that shared checkout. Earlier blocked delivery is resolved. The guest-local copy
is now an earlier snapshot and is not authoritative for subsequent work.

The implementation interview selected initial semantic coefficients (80/20
experience/education; recency groups 1.5/1.25/1.0), success-only extraction
readiness, three failures followed by operator alert/manual retry, a five-second
warm CPU reference benchmark and an 80/20 Portuguese/English evaluation mix.
Mandatory classification requires at least 95% measured precision before it may
exclude a candidate. These decisions are recorded in governing feature and
supporting policy documents; calibration, model choice and production wiring
remain pending.

Added deterministic semantic aggregation with calibrated-score inputs, stable
selection/ties, recency weighting, missing-section normalization, bounds checking
and overflow-safe relative weight normalization. The primitive is not inference
or an implemented production matching pipeline. Tests use supplied per-entry
scores, not fabricated claims of model quality.

Latest shared-checkout validation: **294 tests passed**, no skipped tests in
the isolated database run; Ruff lint and format checks passed (98 files).
`git diff --check` and affected-document file-link checks passed. The user
subsequently selected 80% minimum mandatory-classification recall alongside
95% precision. This is a policy gate awaiting reviewed evaluation, not a model
performance result.

## Open API decision and implementation

The user superseded the earlier authentication requirement: open API, no
authentication, 60 requests/second globally. ADR-009 records the decision. Added
a timestamp-only PostgreSQL admission table/migration and transaction-serialized
rolling limiter at the production ASGI entry point. Independent-instance tests
exercise shared admission, concurrency and expiry; API tests cover privacy-safe
429, Retry-After, fail-closed 503 and unchanged admitted health behavior/no CORS.

Validation: **298 tests passed** against isolated PostgreSQL/pgvector, including
clean migration and existing-data upgrade/downgrade regressions. Production
load/HTTPS deployment and the matching executor remain unfinished.

## User correction: minute quota and pre-production scope

The user corrected the quota to **60 requests per minute globally**, retaining
no authentication. Updated the limiter's default window to 60 seconds and the
429 Retry-After header to 60; added a database regression that seeds 60 admissions
two seconds earlier (must remain blocked) and then ages them beyond 60 seconds
(must admit). ADR-010 supersedes ADR-009's interval without rewriting history.

The user clarified that no production exists and model reprocessing does not
need availability/rolling-consistency machinery. Governing docs now permit simple
stop/reprocess/restart while retaining privacy and fixed-version determinism.

Validation: **299 tests passed** with isolated PostgreSQL/pgvector; Ruff lint/format
and diff checks passed. Orchestration preflight found tmux, Git, gh, sqlite3 and
the existing Codex entry point. No Codex version or update check ran. The
`/home/agent/workspace/agentic-environment` tooling checkout is absent; durable
task orchestration, resource/health gates and full environment acceptance are
not established by this application validation. Continue under the agentic
environment specification, with the already approved host exception.
