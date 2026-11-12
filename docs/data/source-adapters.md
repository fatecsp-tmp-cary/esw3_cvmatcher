# Source adapter contract and APiBR requests

The [MVP source interface](../../specs/feature-001-mvp/spec.md#ingestion-and-normalization)
is implemented by `SourceAdapter` in `src/ingestion/adapters.py` and
`APiBRAdapter` in `src/ingestion/apibr.py`. It separates transport from normalization
and database ingestion. No source schema or public curriculum contract changes.

`discover()` asynchronously yields stable source IDs. Malformed discovery IDs fail
explicitly rather than inventing identities. `fetch_jobs()` asynchronously yields
raw records unchanged, including malformed individual records: ingestion remains
responsible for rejecting those independently. Synchronous `normalize(record)`
uses the existing APiBR normalizer, preserving source identity, explicit availability
and null raw retention. `fetch_job(id)` scans APiBR pages until the ID is found or
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
State-free records remain DISCOVERED; no hidden GitHub verification is enabled.
The worker invokes the bounded synchronous ingestion compatibility path; the
common async adapter is available independently. Live calls remain optional and
excluded from CI.

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

This is explicitly best effort: timestamp/count equality cannot rule out concurrent
rewrites. It does not establish source permissions, job openness, raw retention
rights or #145 absence-driven stale/expiry. Confirmed observations remain source-
specific; all state-free records stay DISCOVERED. The bounded live count probe
is in the [aggregate evidence](../reports/2026-11-12-apibr-count-attestation.json).
