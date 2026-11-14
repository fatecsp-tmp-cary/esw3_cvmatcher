# CV-Match

REST API that receives an already structured CV as JSON and returns job openings ranked by compatibility.

Project documentation starts at [AGENTS.md](AGENTS.md). Product boundaries are in
[scope](docs/product/scope.md), architecture rules in
[architecture invariants](docs/architecture/invariants.md), and the MVP specification,
acceptance criteria, plan, and task status are in
[specs/feature-001-mvp](specs/feature-001-mvp/spec.md). See
[CONTRIBUTING.md](CONTRIBUTING.md) for contributor workflow.

## Local PostgreSQL

Integration/e2e tests and the application use PostgreSQL with pgvector. The
base Compose file pins the selected image digest and keeps the database private.
For local tools, explicitly add the loopback-only development overlay:

```bash
# First time only: copy .env.example to .env if .env does not exist; adjust it.
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Set POSTGRES_PASSWORD in the private environment file. User/database default to
cvmatch; the development port defaults to 127.0.0.1:5432. Change POSTGRES_PORT
and DATABASE_URL together when needed. Check readiness with the same two files
and `compose ps`, or `psql "$DATABASE_URL" -c "select 1;"`.

Stop using `docker compose -f docker-compose.yml -f docker-compose.dev.yml down`.
Retain named volumes; see [deployment and recovery](docs/operations/deployment.md)
for production composition, model preparation and backup procedures.

## Run the complete stack

This is the short path from a checkout to a ranked `POST /matches` response with
the real pipeline. The authoritative procedure, limits and recovery steps are in
[deployment](docs/operations/deployment.md) and [worker](docs/operations/worker.md).

1. Create a private `.env` in the repository root. The stack reaches PostgreSQL
   through the Compose network, so the URL uses host `postgres`:

   ```text
   POSTGRES_PASSWORD=<choose-a-password>
   DATABASE_URL=postgresql://cvmatch:<the-same-password>@postgres:5432/cvmatch
   ```

2. Build the image and prepare the pinned local models. Preparation is the only
   step that downloads anything; serving is offline.

   ```bash
   docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml build api
   docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml --profile prepare run --rm model-init
   docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml --profile prepare run --rm prepare-extraction
   docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml --profile prepare run --rm prepare-embeddings
   ```

3. Start PostgreSQL, apply migrations and register the job source once:

   ```bash
   docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml up -d postgres migrate
   docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml run --rm worker python -m src.worker.sources register apibr --polling-mode SNAPSHOT
   ```

4. Start the worker and the API, then check readiness:

   ```bash
   docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml up -d worker api
   curl --fail http://127.0.0.1:8000/health
   ```

5. Request matches with the synthetic example curriculum:

   ```bash
   curl http://127.0.0.1:8000/matches \
     --header 'Content-Type: application/json' \
     --data @examples/mock_api/curriculum.json
   ```

What to expect:

- The worker polls the source when it starts and then daily at 08:00
  `America/Sao_Paulo`; see the [worker schedule](docs/operations/worker.md#daily-schedule-and-poll-on-start).
- A job is matched only after its extraction and embedding succeed. On the
  one-CPU Compose limit, a local run measured about 25 seconds of extraction per
  job, so the first backlog of several hundred jobs takes hours. `/matches`
  returns an empty list until the first jobs are ready.
- The first `/health` call after a start loads the models and can take longer
  than later calls. Call it once before demonstrating the API.
- The API runs one matching request at a time and admits 60 requests per rolling
  minute; excess requests receive `503` or `429`. See
  [production API admission](#production-api-admission).
- Set `CVMATCHER_API_PORT` in `.env` to publish the API on another loopback port.

Stop the stack with `docker compose --project-name cvmatch -f docker-compose.yml -f docker-compose.production.yml down`; named database and model volumes are kept.

## Runnable API mock

The deterministic mock server lets API consumers try the implemented curriculum
preview’s matching sections and ranked `matches` response without PostgreSQL, a matching model, or
external job sources. It returns the same synthetic result for every valid
request; its score is an example and is not a real compatibility result.

Install the project and run the mock from the repository root:

```bash
pip install -e .
python -m src.mock_api --host 127.0.0.1 --port 8001
```

Send the synthetic example request in another terminal:

```bash
curl --include http://127.0.0.1:8001/matches \
  --header 'Content-Type: application/json' \
  --data @examples/mock_api/curriculum.json
```

To run it in an isolated Docker Compose stack instead, build and start the
mock service with:

```bash
docker compose -f docker-compose.mock.yml up --build
```

The mock is available at `http://localhost:8001`. Set `MOCK_API_PORT` to use a
different host port. Stop the service with
`docker compose -f docker-compose.mock.yml down`.

The mock returns up to 100 deterministic synthetic jobs, controlled by `limit`
(default 10). It also provides `GET /health`, the OpenAPI schema at
`/openapi.json`, and Swagger UI at `/docs`. Use `--host` and `--port` to change
the bind address.
The mock shares the [public request and response contract](specs/feature-001-mvp/acceptance.md#resolved-api-contract)
with the production API, including synthetic job IDs, eligibility, and match details.
Request values, including `curriculo_id`, are not stored, logged, or echoed in errors.

## Database migrations

SQLAlchemy lives in `src/persistence/` and schema changes are versioned with
[Alembic](https://alembic.sqlalchemy.org/) in `migrations/`. Both read the connection
string from the `DATABASE_URL` environment variable (see `.env.example`), so export it
first. The URL can keep the plain `postgresql://` scheme.

```bash
export DATABASE_URL=postgresql://cvmatch:cvmatch@localhost:5432/cvmatch   # bash
```

```powershell
$env:DATABASE_URL = "postgresql://cvmatch:cvmatch@localhost:5432/cvmatch"   # PowerShell
```

With the database running (see above), run from the repository root:

```bash
alembic upgrade head                        # apply all pending migrations
alembic downgrade -1                        # undo the last migration
alembic current                             # show the applied revision
alembic history                             # list all revisions
alembic revision -m "describe the change"   # new empty migration
alembic revision --autogenerate -m "..."    # new migration from model changes
```

Always review an autogenerated migration before committing it. Models inherit from
`Base` in `src/persistence/base.py`; `migrations/env.py` uses its metadata.

The first revision creates a throwaway `tooling_check` table that validates the
tooling. A subsequent migration creates the initial job, source, and source-run
tables. A corrective revision adds canonical job/lifecycle fields while
preserving the initial migration. Later PRs add source-run evidence,
skill/requirement tables and Portuguese search indexes. See [MVP tasks](specs/feature-001-mvp/tasks.md) for current schema status
and remaining ingestion, matching and operational work.

## Tests

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e . --group dev
```

### Running

```bash
pytest                                  # everything except `external`, with coverage
pytest -m unit                          # one category (see markers below)
pytest -m "not integration and not e2e" # skip tests that need PostgreSQL
pytest -m external                      # live-source tests only (opt-in)
pytest tests/api/test_health.py         # a single file
pytest --no-cov -x                      # faster local loop: no coverage, stop at first failure
```

Passing `-m` replaces the default `not external` filter, so combine them when
needed: `pytest -m "unit and not external"`.

### Disposable database test runner

For repeatable isolated tests under the agentic environment, use a rootless
Docker daemon at `/run/user/<uid>/docker.sock`, prepare the existing
`pgvector/pgvector:pg17` image, then run:

```bash
PYTHON=/path/to/working/venv/bin/python scripts/testing/postgres.sh --no-cov -q
```

The helper runs a uniquely labeled database with 512 MiB/one CPU requested,
no host mounts and an ephemeral loopback port. It sets a synthetic `_test` URL,
waits for readiness and removes only its own container/anonymous volumes on exit.
It never uses `.env`, existing database volumes or a rootful Docker socket.
Rootless cgroup enforcement depends on host configuration; check host memory
pressure as well. Tests run serially. No image pull or package installation is
performed by the helper.

### Layout and markers

| Directory | Marker | What goes there |
|---|---|---|
| `tests/unit/` | `unit` | Pure logic: normalization, hashing, lifecycle, scoring. No DB, network or filesystem. |
| `tests/integration/` | `integration` | Components against a real PostgreSQL (+ pgvector) and deterministic source fixtures. |
| `tests/api/` | `api` | HTTP requests/responses through the FastAPI `TestClient`. |
| `tests/e2e/` | `e2e` | Full pipeline: source fixture → ingestion → DB → matching → `POST /matches`. |

The marker is applied automatically from the directory (`tests/conftest.py`);
don't add it by hand. Mirror the `src/` path inside each directory, e.g.
`src/normalization/jobs/` → `tests/unit/normalization/jobs/`.

`external` is set by hand for live-source checks and explicit opt-in local-model performance measurements. They are deselected by default and must never be required in CI.

Conventions:

- Files `test_<subject>.py`, functions `test_<behavior>`. The same file name may
  appear in different directories (`--import-mode=importlib`).
- Unknown markers are errors (`--strict-markers`), and an `xfail` test that
  starts passing fails the run (`xfail_strict`), so it gets cleaned up.
- Shared fixtures go in the nearest `conftest.py`; keep test data deterministic.

### API tests

API tests use FastAPI's `TestClient` (`fastapi.testclient`, backed by `httpx2`).
It runs the ASGI app in-process, so no server or network is needed, and it runs
the app's startup/shutdown events when used as a context manager.

- Build the app through `src.api.app.create_app()`; the `app` and `client`
  fixtures in `tests/api/conftest.py` give each test a fresh instance.
- Assert on status code and JSON body. Invalid request bodies return `422`
  with the failing fields in `errors[*].loc` (error format: [MVP spec](specs/feature-001-mvp/spec.md), REST API).
- For `async` tests that need to await the app directly, use
  `httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app))`.

### Database-backed tests

Integration and e2e tests run against a real PostgreSQL. The fixtures live in
`tests/conftest.py`, so any test under `tests/` can use them.

Setup:

1. Start PostgreSQL (see [Local PostgreSQL](#local-postgresql)).
2. Export `TEST_DATABASE_URL`, pointing at a database whose name ends in `_test`
   (see `.env.example`). The database is created automatically if it does not exist.

```bash
export TEST_DATABASE_URL=postgresql://cvmatch:cvmatch@localhost:5432/cvmatch_test   # bash
```

```powershell
$env:TEST_DATABASE_URL = "postgresql://cvmatch:cvmatch@localhost:5432/cvmatch_test"   # PowerShell
```

Without `TEST_DATABASE_URL` the database tests are skipped. A database name that does not
end in `_test` is refused, so the tests can never touch your development data.

| Fixture | Scope | What it gives you |
|---|---|---|
| `db_engine` | session | Engine for the test database with all migrations applied (`alembic upgrade head` before the run, `downgrade base` after). |
| `db_connection` | test | A connection inside a transaction that is rolled back after the test. |
| `db_session` | test | An ORM `Session` on that connection. Everything a test writes, even after `commit()`, is discarded when it ends. |

Most tests only need `db_session`:

```python
def test_inserts_a_row(db_session):
    db_session.execute(text("INSERT INTO ..."))
    assert db_session.scalar(text("SELECT count(*) FROM ...")) == 1
```

See `tests/integration/persistence/test_database_fixtures.py` for a full example. Run only
these tests with `pytest -m integration`.

Notes:

- Put database tests in `tests/integration/` (or `tests/e2e/`) so they get the right marker.
- Because each test runs inside one transaction, they cannot check behavior between two
  separate connections (for example concurrent inserts). For that, use `db_engine`
  directly and clean up what you create.
- Run the tests serially (no `pytest-xdist`): they share one test database.
- If a PostgreSQL installed on your machine already uses port 5432, set `POSTGRES_PORT`
  (for example `5433`) before `docker compose up -d`, and use the same port in
  `TEST_DATABASE_URL`.

## Production API admission

The production entry point is `src.api.app:app`. Configure `DATABASE_URL` and run
`alembic upgrade head` before starting it with Uvicorn. It intentionally requires
no authentication; configure HTTPS at deployment ingress. The database-backed
quota is 60 admitted requests in any rolling minute across all replicas sharing
the database. All HTTP paths count, including health and docs. Excess requests
receive 429 with `Retry-After: 60`; unavailable admission state returns 503.
See [service access policy](docs/architecture/service-access.md). The production matching executor loads the pinned offline local embedding model and queries current successful extraction/embedding state. Prepare models and run the background worker before expecting ready jobs. See [deployment operations](docs/operations/deployment.md) and [MVP task status](specs/feature-001-mvp/tasks.md) for release limitations.
