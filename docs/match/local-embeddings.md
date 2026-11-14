# Pinned local embeddings

Authority: [MVP spec](../../specs/feature-001-mvp/spec.md),
[ADR-008](../architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md)
and [privacy invariants](../architecture/invariants.md).

The CPU embedding adapter uses `intfloat/multilingual-e5-small` at revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`, producing 384-dimensional vectors.
Its runtime is sentence-transformers 3.4.1 with the approved CPU PyTorch
installation. Production dependency locks own exact package reproducibility.
No paid or hosted inference is used. A job-only provenance row in
`job_embeddings` supplements canonical `Job.embedding`; candidate embeddings and
matching results never enter this table, cache, logs or preparation artifacts.

Prepare the fixed model explicitly before serving:

```bash
python scripts/models/prepare_embeddings.py \
  --cache-dir /path/to/model-cache \
  --manifest /path/to/model-artifacts.json
```

The script fetches only the pinned revision's tokenizer/configuration and
safetensors artifacts, records file SHA-256 hashes, and uses no authenticated
model token or remote custom code. It does not run inference. Model artifacts
and the local manifest are operational files, never repository inputs. The API
and worker use `local_files_only=True` and `trust_remote_code=False`; preparation
is never invoked implicitly. Preparation sets `HF_HUB_DISABLE_TELEMETRY` before
importing the hub library so the library reads it during initialization. Serving may additionally set `HF_HUB_OFFLINE=1`,
`TRANSFORMERS_OFFLINE=1`, and `HF_HUB_DISABLE_TELEMETRY=1`.

`LocalEmbeddingEncoder(EmbeddingConfig(cache_directory=...))` exposes
`encode_queries(texts)`, `encode_jobs(texts)`, `config` and `model_version`.
Queries use `query: ` and jobs use `passage: `. Inference uses CPU, evaluation mode
and `torch.inference_mode()`. Calls are serialized per encoder. Set deployment
`OMP_NUM_THREADS`/`MKL_NUM_THREADS` conservatively for the actual CPU allocation;
these controls do not change matching semantics.

The adapter tokenizes complete entries without truncation, then prepares token-ID
windows including prefix/special-token overhead. Default maximum length is 512,
overlap is 64 tokens, and inference batches contain at most eight windows.
Every content token is covered; a single large entry is never silently shortened
to the model's first window. Window outputs are L2-normalized, combined by the
number of newly covered tokens, and normalized again. Each returned vector must
be finite, nonzero and dimension 384. Empty/whitespace entries are rejected rather
than producing evidence from a prefix; an empty input collection returns empty.
Tokenization retains the full entry's token IDs in memory; batching bounds
inference windows, not the public request size or overall tokenization memory.
No new public collection caps are introduced.

The model version combines the pinned repository revision and a SHA-256 of the
window/aggregation/prefix/dimension and job-passage representation policy. Cache location and batching do not
change this version. Content hash, model/policy version and extraction version
are stored independently, so unchanged source text is regenerated after policy
or model changes. Stop workers before configuration changes; use the accepted
stop/reprocess/restart procedure. `enqueue(session, job_id, config,
extraction_version)` performs invalidation in the caller's transaction. Repeated
same-version enqueue does not reset failed or running work; `retry=True` is an
explicit operator action.

The job passage includes title, explicit skills, sorted unique normalized requirement
texts from the current successful extraction, full cleaned description, location
string values in sorted-key order, and work arrangement. Requirements are read
only after current extraction readiness is established, and publication rechecks
that generation's content hash and extraction version. Reprocessing after an
extraction-version change invalidates the embedding separately from source content.
Equivalent location objects produce the same passage regardless of insertion order.
The revised passage policy changes the model/policy identity, so existing vectors
must be re-enqueued under the new identity before becoming semantically ready.
This does not change canonical Job fields or authorize mandatory exclusions.

`EmbeddingWorker` locks only embedding metadata with PostgreSQL
`FOR UPDATE OF job_embeddings SKIP LOCKED`; its ordinary Job read does not
request a row lock. It commits before
inference, and publishes only under the current token, lease, content and model
configuration. Claims expire after five minutes and consume the same three-attempt
budget when reclaimed. Failed inference/invalid results use 30/60-second backoff;
three failed attempts persist FAILED state and emit a local structured error with
only internal job ID, fixed error category and attempt count. No automatic daily
retry or external alert is introduced. Availability remains independent.

Embedding work requires successful current extraction; completion rechecks it.
Retrieval additionally requires ACTIVE availability, non-null dimension-384
`Job.embedding`, matching successful embedding provenance, and current successful
extraction. `semantic_statement` and `retrieve_semantic` perform exact pgvector
cosine retrieval, then break distance ties by source platform, source job ID and
persisted ID. Returned similarities are `[-1,1]`; empirical calibration and final
per-entry semantic aggregation belong to the matching pipeline. Location/mode
appear only as descriptive job text and never impose geographic eligibility.

Deterministic injected-model unit tests verify complete token coverage, bounded
batches, prefixes, normalization, CPU/eval/inference mode and repeated outputs.
PostgreSQL tests cover claims, content/config invalidation, bounded retries,
readiness, migration round trips and semantic retrieval. The optional actual
local smoke is recorded separately in the runtime report: it is not a measured
five-second complete-request benchmark or independently reviewed calibration.
Production quality and performance acceptance still require those evaluations.
