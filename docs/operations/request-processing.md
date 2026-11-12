# Matching admission, budgets and operational signals

Authority: [ADR-009](../architecture/decisions/ADR-009-open-api-global-rate-limit.md),
[ADR-010](../architecture/decisions/ADR-010-preproduction-and-minute-rate-limit.md) and
[ADR-012](../architecture/decisions/ADR-012-issue-completion-and-evaluation-policy.md).

The API is anonymous. All HTTP paths share the PostgreSQL rolling 60/minute quota,
with privacy-safe 429/Retry-After:60 and fail-closed 503 when admission is unavailable.
A separate process-local slot permits one active matching execution, without a
waiting queue; excess concurrency returns generic RFC-style 503. The execution
owns its slot until it unwinds, including when its client disconnects. Cooperative
checkpoints enforce a 30-second deadline between steps/inference batches. A native
call may finish before cancellation is observed. This adds no public field/body/
collection limits. Unknown source/candidate values are never operational labels.

Enable INFO only for `src.api.app` and `src.matching.pipeline` when inspecting
processing observations. For direct local serving:

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

The HTTP boundary emits `matching_request_duration_ms` and fixed `matching_outcome`
values: success, empty, unavailable or budget_exhausted. This includes unavailable
or unconfigured executors. The pipeline separately emits `matching_duration_ms`.
Do not sum these overlapping measurements. No request bodies, UUIDs, query text,
embeddings or result contents are retained in telemetry. The generic processing
context has no dependency on candidate DTOs or job inference packages.

For Compose, configure these same selective loggers in the process launcher and
inspect `docker compose --project-name NAME -f docker-compose.yml -f
docker-compose.production.yml logs api worker`. Do not enable access/body logging.
Worker observations retain fixed categories and job-only attempt/readiness state;
its separate scheduling/failure policy is implemented by #176.
