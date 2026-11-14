# Job field extraction strategy

Authority: [ADR-008](../architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md)
and the [MVP spec](../../specs/feature-001-mvp/spec.md). Status: local pinned GLiNER inference, state and worker are implemented;
reviewed classification/quality acceptance is pending.

Use GLiNER locally during background job normalization/enrichment. The reference
is the sibling `../gline/README.md`, `extract_requirements.py`, `benchmark.py` and
`VALIDATION.md`, inspected on 2026-11-11. The prototype's multilingual extraction
configuration (`urchade/gliner_multi-v2.1`, threshold 0.3) is an evaluation starting
point, not a production model/threshold decision. Its five-posting qualitative
review is not a release quality gate; source labels are weak labels, not gold data.

1. Preserve cleaned title/description and section boundaries. Extract from bounded
   overlapping chunks with offsets; cover the full supported description, rather
   than silently truncating it. Keep section/context attribution through chunking.
2. Start with skill/tool/framework/database/cloud, education and work-experience
   requirement spans, following the prototype. Evaluate additional canonical field
   targets explicitly before enabling them. Pin model revision, entity labels,
   thresholds, chunk policy and extraction version.
3. Retain span evidence, confidence and context for validation; normalize names via
   shared aliases/taxonomy. Deduplicate overlapping predictions within a job only.
   Never merge jobs across sources or fabricate missing field values.
4. Determine REQUIRED, PREFERRED or NICE_TO_HAVE from explicit contextual evidence.
   Unknown/ambiguous/negated wording stays unclassified. Conflicting strengths use
   the strongest occurrence with an unsafe conflict flag under ADR-018 and cannot
   become a mandatory exclusion. The current requirement-class enum has no UNKNOWN
   value; do not force uncertain output into it. Supporting evidence is persisted
   separately in versioned job extraction state, preserving the canonical Job.
5. Prefer explicit structured source fields; retain conflicts as uncertain evidence
   instead of overwriting source identity, lifecycle, dates or other verified facts.
   Extracted location must never drive geographic eligibility.
6. Track extraction version independently of content hash. Define re-extraction and
   downstream text/vector invalidation when the model, labels, thresholds or mapping
   changes, including unchanged source text. Keep raw retention restrictions.
7. Validate on reviewed PT/EN fixtures: span/field precision and recall, requirement
   classification, ambiguous/negated wording, long descriptions/chunk overlap,
   missing sections, conflicts, CPU runtime and memory. Set numerical acceptance
   targets and failure/retry policy before enabling production extraction. Live
   sources and model downloads must not be required by ordinary CI.

Run extraction outside the candidate request path. A failed extraction must not
manufacture requirements or availability transitions; record a safe failure and
follow the explicit retry policy. Candidate data is not sent through this job
extraction stage. No hosted inference service is introduced.

## Confirmed readiness and failure policy (implementation interview)

The user selected these rules on 2026-11-11:

- A job awaiting extraction, or whose extraction failed, is withheld from **all**
  matching, including textual and structured retrieval. Only successfully
  extracted jobs may enter matching. This is a readiness gate separate from
  availability: do not change ACTIVE/STALE/EXPIRED because extraction failed.
- After three failed extraction attempts, mark extraction failed and alert the
  operator; require an explicit retry. Do not silently retry every day or create
  an unbounded automatic retry loop. Keep the job stored and withheld.
- Supporting extraction readiness/attempt state must be stored separately from
  the fixed canonical Job fields. Persist no candidate information in that state.
- Operator alerts are local only: persist failed-job state and emit a structured
  error log. No webhook/email integration is required by the MVP. Error logs must
  use safe identifiers/failure categories rather than job text or credentials.
- Transient extraction failures wait 30 seconds after the first attempt and 60
  seconds after the second. Only fixed `inference_error` / `invalid_result` categories
  are retained; exception messages and job text never enter errors. Model/configuration
  changes use simple stop/reprocess/restart during pre-production; no availability-
  preserving cutover is required under
  [ADR-010](../architecture/decisions/ADR-010-preproduction-and-minute-rate-limit.md). No alert is sent by this documentation.

The background foundation lives in `src/extraction/service.py`; it uses
`job_extractions` supporting state introduced by migration `b1e001`. It does not
add canonical Job fields or change availability. `enqueue(session, job_id, version)`
creates work or invalidates old content/configuration, in the caller's transaction.
A worker uses `FOR UPDATE SKIP LOCKED` to reserve one job and a random claim token,
then commits before invoking the injected `LocalExtractor`. Current successful
content/configuration is checked by `ready_predicate(version)`; missing, failed,
pending, running and obsolete states fail closed. Retrieval must apply this predicate
separately from ACTIVE availability, on every matching path. Ingestion/API/scheduler
wiring remains the integration owner's responsibility.

Claims expire after five minutes. A crash can then be recovered within the same
three-claim budget; expired/revoked tokens cannot publish a result. A third expired
claim records `FAILED` with fixed `claim_expired` category and emits a local
structured error. A slow inference may consequently be repeated after lease
expiry; this is bounded at-least-once processing, not exactly-once inference.
Repeated terminal failures require explicit operator
`enqueue(session, job_id, version, retry=True)`; merely polling/enqueuing unchanged
content never resets the failure budget. Model/configuration or content changes
start a new extraction generation. Stop workers before changing configuration.

`SpanEvidence` stores character offsets, label and confidence into cleaned
`title + "\n" + description`; source text is not duplicated in error records.
Spans are validated before persistence, duplicate offset/label predictions are
removed, and unclear `requirement_class` stays null. Explicit contextual classes are now
persisted separately as described below. No mandatory exclusions are enabled
by this foundation. `chunks` provides bounded overlapping character windows with
complete coverage and original offsets; token-budget enforcement belongs in the
actual pinned model adapter. Explicit source metadata is untouched.

The initial foundation was verified with synthetic injected extractors. Pinned
GLiNER, taxonomy mapping and API/worker wiring are now implemented; human-reviewed
classification/field quality and release approval remain pending.

## Mandatory classification quality gate

The user selected a minimum **95% measured precision** on independently reviewed
examples before extracted mandatory requirements may cause candidate exclusion.
This is mandatory-classification precision, not the entity model's confidence
threshold and not a universal correctness guarantee. Unknown/conflicting context
still cannot cause exclusion. The user also selected minimum **80% measured recall** for mandatory
classification. Sample counts and field/span targets are resolved in ADR-012; threshold fitting
awaits the reviewed calibration cases. Review labels independently
of source weak labels and GLiNER predictions; report sample counts and PT/EN
results alongside the combined 80% Portuguese / 20% English evaluation mix.

## Reviewed sample and field targets

Under [ADR-012](../architecture/decisions/ADR-012-issue-completion-and-evaluation-policy.md),
the user reviews at least 40 PT/10 EN blind cases. Half of each language is used
for calibration and half held out. Field/span precision >=90% and recall >=80%
are required per language; mandatory classification retains >=95% precision and
>=80% recall. Undefined metrics or missing positive examples fail acceptance.
Thresholds must be fixed using calibration only before held-out measurement.
These decisions do not convert the existing failed synthetic run into a pass.

## Context classes and shared taxonomy

`src/extraction/classification.py` classifies local GLiNER spans only from explicit
PT/EN sentence or immediate section-heading cues. Negation remains null; hedges are NICE_TO_HAVE. Contradictory cues
and conflicting occurrences retain the strongest strength with conflict flags under ADR-018. Presence or confidence alone never
establishes a required skill. `src/extraction/persistence.py` atomically replaces
current JobRequirement/JobSkill associations with successful claim completion.
The versioned project-maintained alias seed has canonical technology names,
additive aliases, category `technology` and null parents for flat roots. Existing
curated categories/parents are preserved. Repeated seeding preserves identities.
No external taxonomy provenance or inferred hierarchy is claimed. Candidate
matching uses the same explicit aliases transiently. The extraction-version hash
includes classification and seed versions, forcing unchanged-content reprocessing
when those policies change. Canonical Job content/hash is not mutated by these
supporting associations. Mandatory exclusions remain disabled pending review.

## Corrected extraction policy

[ADR-018](../architecture/decisions/ADR-018-extraction-context-and-approximate-evidence.md)
is the authority for clause-local classification, smallest meaningful spans,
strongest occurrence consolidation and bounded typo support. `annotate_spans`
annotates every detection in place and returns only selected requirements. Raw
evidence retains original detection offsets, occurrence classes, negation,
conflict, approximation and selection flags. `exclusion_safe` is always false.
Negated mentions remain null; background detections remain inspectable without
becoming requirements. Exact aliases are authoritative; approximate matches
produce score-only associations, never canonical requirement FKs or new aliases.
All candidate lookup remains transient. Dedicated model labels are professional
credential/license, language and certification, in addition to existing labels.
These policy changes are hashed into extraction version/provenance and require
re-extraction of unchanged jobs before readiness and downstream publication.

Updated calibration/old-held-out labels are versioned policy adjudications; original
reviewed evidence and failed results remain historical. The old held-out cases
have been diagnosed and are no longer independent acceptance evidence.

Exact project aliases also supplement model detections, with explicit source
provenance. They do not infer strength and do not replace local GLiNER. Cue-only
spans are not meaningful entities. This follows the feature's existing dictionary
complement policy; neither source fields nor the canonical schema change.


## PR #170 review corrections

Clause-local negation also covers an omitted predicate: “Python required, but not
Java” and “Python obrigatório, mas não Java” retain Java as detected null evidence
without a positive requirement/skill association. “Not only” and “não só” retain
their affirmative meaning. Known headings with inline content, such as
“Benefits: health insurance”, terminate requirement scope; inline requirement
headings supply fallback strength. Sentence-local team-context labels do not
suppress an explicit later requirement on the same line.

These deterministic corrections version classification as
`clause-strongest-negation-hedge-conflict-v4` and context as
`sentence-clause-sections-v3`, changing `EXTRACTION_VERSION`. Apply the existing
stop/reprepare/reprocess/restart procedure before using corrected artifacts.
Frozen annotation copies, calibration outputs and prior failures remain unchanged;
those results do not calibrate this revised runtime. Exclusions and release
approval remain disabled. See the
[review record](../reports/2026-11-14-pr170-review.md).
