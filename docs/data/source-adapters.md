# Source adapter contract and APiBR requests

The [MVP source interface](../../specs/feature-001-mvp/spec.md#ingestion-and-normalization)
is implemented by `SourceAdapter` in `src/ingestion/adapters.py` and
`APiBRAdapter` in `src/ingestion/apibr.py`. It separates transport from normalization
and database ingestion. No source schema or public curriculum contract changes.

`discover()` asynchronously yields stable source IDs. Malformed discovery IDs fail
explicitly rather than inventing identities. `fetch_jobs()` asynchronously yields
raw records unchanged, including malformed individual records: ingestion remains
responsible for rejecting those independently. Synchronous `normalize(record)`
uses the existing APiBR normalizer, preserving source identity and null raw
retention. Under accepted ADR-014, listing presence is open-vacancy evidence:
state-free records become ACTIVE and successful ingestion advances verification;
explicit closure is EXPIRED and terminal expiration cannot be reopened. Vacancy-level category aliases follow the
[issue #180 mapping](../../specs/feature-001-mvp/spec.md#apibr-vacancy-label-mapping):
exactly one distinct category is required, conflicting evidence stays unknown,
and every source label name stays in `keywords`. Repository topics never establish
vacancy categories. This supersedes #168's earlier first-recognized-label behavior.
`fetch_job(id)` scans APiBR pages until the ID is found or
an empty page is observed. APiBR has no verified single-record endpoint here; this
operation can be expensive. Prefer `fetch_jobs()` for polling. No method silently
requests GitHub job URLs or verifies availability elsewhere.

By default APiBR declares `INCREMENTAL` and `snapshot_complete=False`. Sequential pages stop
at the first empty page; the 1,000-page safety limit fails the scan if no empty
page was reached. Neither an empty page nor a missing `fetch_job` result establishes
absence, expiration or complete snapshot coverage by itself. Explicit SNAPSHOT
mode follows the accepted ADR-013 attestation below. Live source access/retention
permissions remain unverified under
[ADR-002](../architecture/decisions/ADR-002-apibr-mvp-source.md) and
[ADR-003](../architecture/decisions/ADR-003-apibr-availability-and-partial-runs.md).
The adapter does not persist raw responses.

The synchronous `APiBRClient` is retained for existing `ingest_apibr` callers and
uses the same single-request implementation as the async adapter. Its injected
transport accepts an HTTP request and a 15-second timeout, returning JSON bytes.
Default transport uses the Python standard library; no added package is needed.
The async adapter runs each blocking HTTP call in a thread and waits between
retries in the event loop. Cancellation interrupts retry waits. An in-flight
blocking request may continue until its transport timeout; this is not a hard
cancellation guarantee.

The request policy permits three total attempts per page by default (configurable
from one through three). HTTP 429, HTTP 5xx, and URL/network/OS failures may retry;
other HTTP statuses, malformed JSON, non-array pages and unexpected transport
failures do not. Backoff starts at one second, then two seconds. A valid
`Retry-After` integer delay or HTTP date overrides backoff, bounded to zero through
60 seconds; invalid values use backoff. Delay settings are finite and bounded.
There is no retry after the final attempt. These are page-level limits, not a
claim of a complete scan-duration bound. Scheduler-level polling limits remain
separate work.

`SourceError` exposes only a fixed failure category, never upstream exception
messages, URLs or response bodies. Existing ingestion still records safe exception
types, rolls back the run's job changes after page failure, and commits valid
individual records as `PARTIAL` when normalization rejects others. Transport,
clock and sleep injection keep unit/integration tests deterministic and offline.
No live-source or model download is a CI prerequisite.

The worker/scheduler integration of this async interface remains pending. This
change supplies the common adapter and bounded request behavior; it does not
establish source permissions, full MVP ingestion operations, or release readiness.

## Optional current shape observation

A primary-only, one-record read-only probe on 2026-11-12 returned HTTP200 and
an array with id/title/body/url/created_at and keyword/label fields. The returned
record had no availability state. Only aggregate keys/counts were retained in
[the probe report](../reports/2026-11-12-source-shape.json); no upstream record or
poster information was saved. This establishes a current example of endpoint
shape, not completeness, stable long-term guarantees or retention rights.
Under accepted
[ADR-014](../architecture/decisions/ADR-014-apibr-listing-presence-is-open-evidence.md),
listed state-free records are ACTIVE; no hidden GitHub verification is enabled.
The worker invokes the bounded synchronous ingestion compatibility path; the
common async adapter is available independently. Live calls remain optional and
excluded from CI.

## Current field mapping and displayed skills

Authority: [ADR-019](../architecture/decisions/ADR-019-title-first-job-evidence-and-displayed-skills.md), which supersedes the proposed ADR-017 precedence and display behavior while preserving ADR-017.

Observed APiBR labels include `name`, `type`, and `color`, plus title-derived `keywords`. Repository `topic` labels are ignored for field classification; all source label names remain keywords. Shared exact aliases map recognized fields. Leading decorative symbols and supported `Level-`/`Lang-` prefixes are removed before lookup.

| Canonical field | Source evidence | Rule |
| --- | --- | --- |
| `seniority_level` | title, usable typed labels, explicit named/checked body fields | Title wins first; multiple values use the ADR-019 order, with first occurrence breaking the specialist/coordinator tie. Conflicting labels may fall through to checked body options. |
| `work_arrangement` | title, usable typed labels, explicit named/checked body fields | Title wins first; multiple values use REMOTE < HYBRID < ON_SITE. Conflicting labels may fall through to checked body options. |
| `skills` | source labels plus current extraction provenance | The public result adds only exact, affirmative, non-negated, non-conflicting extracted skills. Stored source fields and score associations remain unchanged. |
| `keywords` | every source label name | Retained unchanged, including topics. |

Body evidence is restricted to named fields such as `Nível: pleno` or `Localização: Remoto`, and checked options in recognized sections. Free prose is not interpreted. An unambiguous label is used only when the title contains no recognized value; a conflicting label set can fall through to valid body evidence. Unknown categories stay empty. `company`, `location`, and `salary` remain empty because APiBR provides no structured source fields for them. Work arrangement never drives geographic eligibility.

Field mapping changes participate in content hashing and re-queue extraction and embedding. Displayed extracted skills require matching current successful extraction evidence; a `JobSkill` association alone is not proof of display trust. The deterministic `tests/resources/apibr_v2_issues.json` fixture uses synthetic records only. Current implementation and verification are recorded in the [PR #197 review](../../docs/reports/2026-11-15-pr197-review.md).

## Accepted best-effort SNAPSHOT mode

[ADR-013](../architecture/decisions/ADR-013-best-effort-apibr-snapshot-attestation.md)
supersedes the earlier blanket completeness limitation, not availability rules.
The default remains INCREMENTAL/incomplete. Operators explicitly configure
`JobSource.polling_mode = "SNAPSHOT"` for synchronous worker ingestion, or construct
`APiBRAdapter(..., polling_mode=PollingMode.SNAPSHOT)` for async consumers.

The client reads `/health` before and after issues-with-body pagination using the
same bounded transport policy. A source body-dataset health signature contains
only records, last_updated and from_backup. Completeness requires healthy stable
signatures, exact distinct normalized source-ID count, a terminal empty page and
zero duplicates/invalid IDs/rejections/request failures. A successful retry still
invalidates completeness. Unsupported clients/missing health and incremental
configurations never qualify. SourceRun.snapshot_evidence stores only bounded
counts/signatures/policy flags in JSONB migration b1e006, not IDs, authors or raw
responses. Async cancellation/truncation cannot publish completed attestation.

Synchronous ingestion captures both health signatures and all remote pages before
acquiring the bounded, ordered identity-lock stripes. It then applies buffered
observations in source order within one transaction. Persistence-phase rejections
update the stored evidence's rejection count and invalidate qualification without
another remote call. Network failure leaves job changes rolled back; a rejected
record still permits valid observations to commit as PARTIAL.

This is explicitly best effort: timestamp/count equality cannot rule out concurrent
rewrites. It does not establish source permissions, job openness, raw retention
rights or implementation of the #145 stale-expiry counters. ADR-020 now defines
the accepted count-only threshold. Accepted
[ADR-015](../architecture/decisions/ADR-015-qualifying-snapshot-absence-marks-stale.md)
marks ACTIVE jobs absent from a qualifying snapshot STALE. Confirmed observations remain source-
specific; listed state-free records are ACTIVE under ADR-014. The bounded live
count probe
is in the [aggregate evidence](../reports/2026-11-12-apibr-count-attestation.json).

## Accepted field policy implementation

ADR-019 is implemented in PR #197. The normalizer applies title > typed labels > named/checked body fields, approved restrictive value orders and first-occurrence tie handling. Result skills are provenance-filtered without changing stored canonical skills. ADR-017 remains preserved as the original proposal.

## MeuPadrinho adapter, JSONL import, and availability validation

Authority: [ADR-025](../architecture/decisions/ADR-025-meupadrinho-source-and-validation.md).

`MeuPadrinhoAdapter` and `MeuPadrinhoClient` in `src/ingestion/meupadrinho.py` and `normalize_meupadrinho_job` in `src/normalization/jobs/meupadrinho.py` integrate MeuPadrinho (`platform="meupadrinho"`, `source_job_id=nano_id`):

- Direct mapping translates `nome_empresa` -> `company`, `titulo_vaga` -> `title`, `descricao_vaga` (+ `requisitos_desejaveis`) -> `description`, `local` -> `location`, `forma_trabalho` -> `work_arrangement`, `nivel_vaga` (fallback `nivel`) -> `seniority_level`, `;`-split `requisitos_tecnicos` -> `skills`, `salario` -> `salary` + `currency="BRL"`, `link_vaga` > `link_vaga_publicado` > `link_plataforma_publicado` > `https://meupadrinho.com.br/api/vagas/{nano_id}` -> `job_url`, and `horario_registro` -> `publication_date`.
- `ingest_meupadrinho_jsonl` and `python -m src.worker --import-meupadrinho <path>` import JSONL dumps produced by `meu_padriho.sh` with per-record savepoints and `SourceRun` tracking.
- Scheduled polling via `ingest_meupadrinho` validates active/non-expired MeuPadrinho jobs in bounded batches (`GET /api/vagas/{nano_id}` ordered by oldest `last_verified_at`), marking `vaga_encerrada=True` or HTTP `404` as `EXPIRED`.
- `MeuPadrinhoClient` enforces MeuPadrinho's 60 requests/second rate limit via `RateLimiter(60.0)` and uses `RetryPolicy(jitter_ratio=0.2)` for jittered exponential retry backoff. Both `RetryPolicy` and `RateLimiter` in `src/ingestion/adapters.py` are shared across source adapters.
