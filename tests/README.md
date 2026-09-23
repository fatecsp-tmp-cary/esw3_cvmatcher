# Tests

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux/macOS: source .venv/bin/activate
pip install -e . --group dev
```

`pip install --group` requires pip 25.1 or newer (`python -m pip install --upgrade pip`).

## Running

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

## Layout and markers

| Directory | Marker | What goes there |
|---|---|---|
| `tests/unit/` | `unit` | Pure logic: normalization, hashing, lifecycle, scoring. No DB, network or filesystem. |
| `tests/integration/` | `integration` | Components against a real PostgreSQL (+ pgvector) and deterministic source fixtures. |
| `tests/api/` | `api` | HTTP requests/responses through the FastAPI `TestClient`. |
| `tests/e2e/` | `e2e` | Full pipeline: source fixture → ingestion → DB → matching → `POST /matches`. |

The marker is applied automatically from the directory (`tests/conftest.py`);
don't add it by hand. Mirror the `src/` path inside each directory, e.g.
`src/normalization/jobs/` → `tests/unit/normalization/jobs/`.

`external` is the only marker set by hand, on tests that reach a live job
source. They are deselected by default and must never be required in CI.

Conventions:

- Files `test_<subject>.py`, functions `test_<behavior>`. The same file name may
  appear in different directories (`--import-mode=importlib`).
- Unknown markers are errors (`--strict-markers`), and an `xfail` test that
  starts passing fails the run (`xfail_strict`), so it gets cleaned up.
- Shared fixtures go in the nearest `conftest.py`; keep test data deterministic.

## API tests

API tests use FastAPI's `TestClient` (`fastapi.testclient`, backed by `httpx2`).
It runs the ASGI app in-process, so no server or network is needed, and it runs
the app's startup/shutdown events when used as a context manager.

- Build the app through `src.api.app.create_app()`; the `app` and `client`
  fixtures in `tests/api/conftest.py` give each test a fresh instance.
- Assert on status code and JSON body. Invalid request bodies return `422`
  with the failing fields in `detail[*].loc`.
- For `async` tests that need to await the app directly, use
  `httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app))`.

Never use real CVs or personal data in payloads or fixtures.
