# ADR-025: MeuPadrinho source adapter, JSONL import, and bounded availability validation

- **Status:** Accepted
- **Date:** 2026-11-17
- **Authority:** User request and interview on 2026-11-17.
- **Supersedes:** Only the second-source deferral in [ADR-023](ADR-023-deferred-external-deployment-and-second-source.md); external deployment deferral in ADR-023 and all other architectural invariants remain unchanged.
- **Implementation status:** Implemented in `src/normalization/jobs/meupadrinho.py`, `src/ingestion/meupadrinho.py`, `src/worker/scheduler.py`, `src/worker/sources.py`, `src/worker/bootstrap.py`, `src/worker/runtime.py`, and `src/worker/__main__.py`.

## Context

The project now includes a structured MeuPadrinho (`meupadrinho.com.br`) dataset and collection script (`tmp/meupadrinho/meu_padriho.sh`) producing JSONL records (`{"nano_id": ..., "contents": {...}}`). Unlike APiBR, MeuPadrinho provides structured fields (`nome_empresa`, `titulo_vaga`, `descricao_vaga`, `local`, `forma_trabalho`, `nivel_vaga`, `nivel`, `requisitos_tecnicos`, `requisitos_desejaveis`, `salario`, `link_vaga`, `link_plataforma_publicado`, `horario_registro`, and `vaga_encerrada`), as well as a per-job detail endpoint (`GET https://meupadrinho.com.br/api/vagas/{nano_id}`).

## Decision

1. **Source identity and registration:** Register `"meupadrinho"` as a supported source in `SUPPORTED_SOURCES` (`src/worker/sources.py`) and wire `ingest_meupadrinho` into `SourceScheduler`'s default pollers. Canonical records use `platform="meupadrinho"` and `source_job_id=nano_id`. Cross-source records remain independent (no cross-platform deduplication).
2. **Direct canonical field mapping:**
   - `company`: `nome_empresa`
   - `title`: `titulo_vaga`
   - `description`: `descricao_vaga`, appending `Requisitos desejáveis:\n<requisitos_desejaveis>` when non-empty so downstream GLiNER extraction can classify preferred requirements.
   - `location`: parsed into `{"city": ..., "state": ..., "country": ..., "raw": ...}` when unambiguous (`"City, UF"`, `"City, Brasil"`, `"Brasil"`, `"City, State, Country"`), preserving `"raw"` for all non-empty strings.
   - `work_arrangement`: `forma_trabalho` mapped via `normalize_work_arrangement` (including the observed `"presecial"` typo -> `ON_SITE`).
   - `seniority_level`: `nivel_vaga` with fallback to `nivel`, mapping `Staff` -> `SPECIALIST` and `Techlead` / `Diretor` -> `COORDINATOR`.
   - `skills`: `;`-separated items from `requisitos_tecnicos`, mapping recognized aliases via `canonical_skill` while preserving other technical terms, deduplicated case-insensitively and sorted.
   - `salary` and `currency`: numeric values/ranges in `salario` parsed to `{"min": ..., "max": ...}` with `currency="BRL"`; `None` for both when `salario` is empty or non-numeric (e.g. `"0,00"`, `"A combinar"`).
   - `job_url`: priority `link_vaga` > `link_vaga_publicado` > `link_plataforma_publicado` > `"https://meupadrinho.com.br/api/vagas/{nano_id}"`.
   - `publication_date`: `horario_registro` normalized to UTC.
   - `status`: `EXPIRED` when `vaga_encerrada` is `True`, otherwise `ACTIVE`.
3. **JSONL ingestion and CLI:** Provide `ingest_meupadrinho_jsonl(session, source_id, path)` and CLI flag `python -m src.worker --import-meupadrinho <path>` to ingest JSONL dumps produced by `meu_padriho.sh` with per-record savepoints and `SourceRun` tracking, without requiring model artifacts to be loaded during the import command.
4. **Worker availability validation, rate limiting, and backoff/jitter protocol:**
   - **MeuPadrinho rate limit (`60 req/s`):** `MeuPadrinhoClient` enforces a bounded `RateLimiter` (`MEUPADRINHO_MAX_REQUESTS_PER_SECOND = 60.0`, minimum interval `1/60s`) before every HTTP request across both synchronous and async adapter calls, paired with `RetryPolicy(jitter_ratio=0.2)` exponential backoff (`1s`, `2s`, capped at `60s`, honoring `Retry-After` on HTTP `429`/`5xx`).
   - **Unified worker backoff & jitter:** All workers support injectable, deterministic-default jitter and backoff: `RetryPolicy(jitter_ratio=...)` and `RateLimiter` for source HTTP adapters (`APiBRClient`, `MeuPadrinhoClient`), `SourceScheduler(..., jitter_seconds=...)` for poll scheduling, `ExtractionWorker(..., retry_jitter_seconds=...)` and `EmbeddingWorker(..., retry_jitter_seconds=...)` for transient inference retry backoff (`30s * attempts + jitter`), and `BackgroundWorker.run_forever` exponential cycle backoff (`poll_seconds * 2^consecutive_error_cycles` capped at `max_backoff_seconds`) with `poll_jitter_seconds`. Production composition (`create_default_worker`) enables jitter across these components while unit/integration defaults remain `0.0` for deterministic test assertions.
   - When `SourceScheduler` polls `meupadrinho`, `ingest_meupadrinho` selects up to a bounded batch (`validation_limit=50` by default) of non-expired `meupadrinho` jobs ordered by oldest `last_verified_at` (nulls first) and queries `GET https://meupadrinho.com.br/api/vagas/{nano_id}`. Jobs returning `vaga_encerrada=True` or HTTP `404` transition to terminal `EXPIRED`; open jobs update their content/verification timestamp. Optional live discovery (`discover_new=True`) is also supported.

## Consequences

- MeuPadrinho jobs can be bulk-imported from JSONL dumps and continuously validated for availability by the background worker, then enriched by the existing GLiNER extraction and E5 embedding stages.
- `SNAPSHOT` completeness remains `False` for MeuPadrinho runs; expiration is driven by explicit `vaga_encerrada=True` or HTTP `404` on the detail endpoint, never by listing absence.
