# Dependency locks

`pyproject.toml` is the dependency authority. Five generated `.in`/`.lock`
pairs under `requirements/` cover build tools, runtime, development (including
runtime), local CPU models (including runtime), and pip-tools itself.
`provenance.json` records SHA-256 digests of every input and lock. The supported
lock target is Linux x86_64 with Python 3.12; other platforms need verification.

## Update procedure

Use a reviewed Python 3.12 environment with the locked pip-tools installed.
Do not refresh dependencies as part of ordinary CI. From the repository root:

```sh
python scripts/dependencies/inputs.py
python -m piptools compile --allow-unsafe --generate-hashes --no-emit-index-url --no-emit-trusted-host --output-file=requirements/build.lock requirements/build.in
python -m piptools compile --allow-unsafe --generate-hashes --no-emit-index-url --no-emit-trusted-host --output-file=requirements/tooling.lock requirements/tooling.in
python -m piptools compile --allow-unsafe --generate-hashes --no-emit-index-url --no-emit-trusted-host --output-file=requirements/runtime.lock requirements/runtime.in
python -m piptools compile --allow-unsafe --generate-hashes --no-emit-index-url --no-emit-trusted-host --output-file=requirements/dev.lock requirements/dev.in
python -m piptools compile --allow-unsafe --generate-hashes --no-emit-index-url --no-emit-trusted-host --extra-index-url https://download.pytorch.org/whl/cpu --output-file=requirements/local-models.lock requirements/local-models.in
python scripts/dependencies/inputs.py --record
python scripts/dependencies/inputs.py --check
```

Review version/hash changes before recording provenance; `--record` attests
artifacts, it does not independently verify registry ownership. Existing pins
are retained unless intentionally upgraded with pip-compile's upgrade options.
Keep `--allow-unsafe` when generating build/tooling/CPU locks: pip-tools otherwise
omits required setuptools/pip entries even with hashes enabled. The tooling and
CPU inputs constrain setuptools through `build.lock`, so regenerate build first.
Keep the exact CPU torch and inference versions in pyproject. Never put private
index credentials in inputs, generated headers, provenance or logs.

In a clean environment install `build.lock`, `dev.lock` and `local-models.lock`
with `pip install --require-hashes -r ...` (the CPU lock needs the extra index
above), then `pip install --no-deps --no-build-isolation -e .` and `pip check`.
The tooling lock is for maintainers, not the serving image. The offline check
uses only the standard library: it verifies pyproject projections, all five
pairs, exact pins/hash syntax and recorded artifact digests without resolving or
downloading anything. It also checks included lock packages, overlapping build
constraints, and shared development/local-model pins because CI installs those
environments together. Pip enforces distribution hashes at installation time.

## CI and serving

Existing CI retains lint, format, mypy, unit/API, PostgreSQL integration/e2e and
production image build jobs. It also checks lock consistency and runs migration
upgrade/downgrade/upgrade plus `alembic check` against the pinned pgvector image.
Ordinary CI installs inference libraries but never downloads model weights or
requires live sources/models; use synthetic fixtures for inference tests.

The Dockerfile installs hashed build and CPU runtime dependencies, copies the
model preparation scripts and runs as UID 10001 with inference offline and
Uvicorn access logs disabled. Prepare reviewed model artifacts separately using
`scripts/models/` and mount readable caches at the configured model paths before
serving; the image build does not fetch weights. Keep candidate data out of
logs and preserve the PostgreSQL global 60-per-minute admission policy.
Container build, database migration and clean-host acceptance require execution;
lock consistency alone does not establish those deployment results. See the
[Definition of Done](../quality/definition-of-done.md) and
[architecture invariants](../architecture/invariants.md).

## Resolver cache maintenance

Initial CPU hash generation can take about 15 minutes and retain several GiB of
HTTP distribution payloads. Preserve completed locks/provenance before cleanup,
and wait for all pip/pip-tools processes using the cache to exit. To reclaim
large downloads while retaining most useful index metadata, remove only `.body`
files at least 10 MiB beneath the resolver's `pip-tools/http-v2` cache. Smaller
bodies and response metadata can remain; later resolution may download removed
payloads again. This cache is separate from model artifacts and application data.
Never remove model caches or another running task's downloads as part of this
procedure. Coordinate cleanup and subsequent image builds with the primary.
