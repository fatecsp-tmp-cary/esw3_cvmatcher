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

APiBR declares `INCREMENTAL` and `snapshot_complete=False`. Sequential pages stop
at the first empty page; the 1,000-page safety limit fails the scan if no empty
page was reached. Neither an empty page nor a missing `fetch_job` result establishes
absence, expiration or complete snapshot coverage. Live source access/retention
permissions, actual endpoint payloads and completeness remain unverified under
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
