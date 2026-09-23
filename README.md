# CV-Match

REST API that receives an already structured CV as JSON and returns job openings ranked by compatibility.

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
pytest                 # all tests, with coverage
```

### API tests

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
