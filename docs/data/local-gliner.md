# Pinned local GLiNER extraction

Authority: [ADR-008](../architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md)
and the [extraction policy](job-field-extraction.md). This adapter implements
local inference; it does not establish model/classification quality or release readiness.

`src.extraction.gliner.GlinerExtractor(directory)` implements `LocalExtractor`.
`EXTRACTION_VERSION` hashes the pinned model/tokenizer revisions, labels,
provisional threshold, chunk/overlap/dedup policy and inference package versions.
The worker stores that version separately from canonical Job fields.

Artifacts are explicitly prepared before serving:

```bash
python scripts/models/prepare_extraction.py /path/to/model-cache/gliner
```

The preparation command downloads only `model.safetensors` and configuration
from `urchade/gliner_multi-v2.1` revision
`443d26d654e0324125a96bebd8e796c14ff2efe6`; and `config.json`,
`tokenizer_config.json`, `spm.model` from `microsoft/mdeberta-v3-base` revision
`a0484667b22365f84929a935b5e50a51f71f159d`. It never downloads pickle weights,
remote Python modules or backbone weights. The exact backbone configuration is
embedded into a derived GLiNER configuration; the upstream configuration is
preserved separately. SHA-256 hashes of every serving artifact and source
revision are recorded in `provenance.json`. A completed directory is published
atomically; existing directories are validated, not overwritten. Failed staging
directories remain for explicit inspection/recovery.

Serving validates hashes/policy first and loads only the local directory with
`local_files_only=True`. The local pinned tokenizer files are colocated with
the GLiNER configuration, so GLiNER never falls back to the backbone repository's
mutable default branch. Embedded backbone configuration prevents an implicit
configuration lookup. Remote `auto_map` configurations are rejected. The selected
runtime is CPU, one Torch thread, evaluation mode and safetensors with strict
state-dictionary loading. The adapter verifies GLiNER 0.2.30, Transformers 4.57.6
and Torch 2.9.1+cpu before inference. The selected SentencePiece 0.2.3
tokenizer conversion additionally requires compatible Protobuf 7.36.1; pin these
transitive dependencies in the application lock. Neither serving nor ordinary tests download models.
Set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` in deployment as an additional
operational safeguard; preparation is the sole intentional network step.

The provisional labels are `skill`, `tool`, `framework`, `database`, `cloud`,
`education`, `work experience requirement`, `professional credential`,
`professional license`, `language`, `certification`; threshold is 0.3. Labels/confidence
never imply mandatory status. Occurrence classes are assigned only by explicit clause/section context under
[ADR-018](../architecture/decisions/ADR-018-extraction-context-and-approximate-evidence.md).
Unknown/negated detections remain null. Classification supports scores only;
all new hard exclusions remain disabled regardless of assigned strength. Structured source metadata, canonical
Job fields and lifecycle remain untouched.

Each input is the worker's cleaned title, newline and description. Windows cover
every original character with at most 1,200 characters and up to 200 characters
of overlap (reduced for short windows to guarantee forward progress). Before
inference, every window is checked against the exact tokenizer input assembled
by GLiNER's label prompt and word splitter: at most 384 words and 384 subtokens,
with tokenizer truncation disabled during the check. Windows are reduced until
they fit. An unrepresentable single character fails the job rather than silently
truncating. The same runtime tokenizer limit is 384, below the pinned backbone's
512-position capacity. Offsets remain Python character offsets into original
cleaned text, including accented text and supplementary Unicode characters.

Predictions require valid labels, finite bounded confidence, offsets within the
window, and exact agreement between span text and source substring. Malformed
predictions fail extraction. Below-threshold predictions are ignored. Overlapping
predictions of the same label are resolved by highest confidence, then longest
span and stable offset order; final output is sorted by original offsets/label.
This merges evidence within one job only and never merges source jobs.

`src.extraction.taxonomy` provides explicit aliases and bounded phrase matching:
`normalize_skill`, `canonical_skill` and `find_skills`. Exact aliases preserve punctuation in C++, C# and Node.js. Unknown terms of
at least five characters may have one unique edit-distance match, including an
adjacent transposition, with punctuation/word boundaries preserved. This approximate
match supports scoring only and does not manufacture canonical equivalence,
mandatory satisfaction or permanent aliases. Shared candidate lookup uses the
same policy without storing or logging candidate data.

Offline tests inject a model backend and exercise coverage, offsets, invalid
predictions, aliases, provenance corruption and the exact token budget. Actual
synthetic PT/EN model smoke results are recorded in the orchestration task report.
A smoke invocation proves the pinned artifacts execute locally; it is not an
independently reviewed quality dataset, calibration or five-second request benchmark.

## Local synthetic smoke evidence

On 2026-11-11 the pinned artifacts executed with `HF_HUB_OFFLINE=1` and
`TRANSFORMERS_OFFLINE=1`, CPU/one thread, on four synthetic Portuguese job
descriptions and one English description. Outputs contained 5/8/5/4/6 spans;
all offsets were valid, every requirement class remained null, and repeated
evaluation of a fixed input produced identical evidence. Loading took 8.409
seconds; individual extraction calls took 1.081/0.441/0.363/0.284/0.280 seconds.
Peak process RSS was 1,061,772 KiB. These are small-job smoke results, not the
complete matching benchmark or quality evaluation. The safetensors SHA-256 was
`2100142f31627531497850659dcb3821c99d5e71c08a8e01a98e4b11ef32a199`.

Transformers emitted two tokenizer warnings: fast SentencePiece conversion lacks
byte fallback, so some characters may become unknown tokens; and its generic
Mistral-regex diagnostic appeared for this mDeBERTa tokenizer. The adapter leaves
the pinned conversion semantics unchanged rather than applying a model-specific
regex workaround from another architecture. PT/EN quality evaluation must measure
these limitations before release. Initial smoke attempts exposed missing and then
incompatible Protobuf dependencies; the final compatible pin above resolved both.

## Corrected detection and projection

GLiNER remains the local model detector. Exact occurrences from the explicit
project vocabulary supplement missed model entities; they carry
`detection_source=exact_alias`. Their confidence 1.0 denotes an exact lexical
match, not a calibrated model probability or mandatory status. No fuzzy offsets
are synthesized. The same clause classifier and selection rules govern both
sources; cue-only model spans are retained but not selected as entities.
Generic seniority/experience/credential wrappers are trimmed without losing
meaningful quantities or original Unicode offsets. Raw detection offsets remain
available beside selected entity boundaries. The project vocabulary includes
explicit CNH category names separately; categories are never inferred or merged.
