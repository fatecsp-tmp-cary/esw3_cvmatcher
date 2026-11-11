# Job field extraction strategy

Authority: [ADR-008](../architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md)
and the [MVP spec](../../specs/feature-001-mvp/spec.md). Status: planned.

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
   Unclear/conflicting wording stays unclassified supporting evidence and cannot
   become a mandatory exclusion. The current requirement-class enum has no UNKNOWN
   value; do not force uncertain output into it. Design any supporting evidence
   persistence separately before implementation.
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
- Retry delay and failure categories still need definition. Model/configuration
  changes use simple stop/reprocess/restart during pre-production; no availability-
  preserving cutover is required under
  [ADR-010](../architecture/decisions/ADR-010-preproduction-and-minute-rate-limit.md). No alert is sent by this documentation.

These requirements are accepted; the worker, evidence persistence, readiness
queries and operator alert/retry mechanism remain unimplemented.

## Mandatory classification quality gate

The user selected a minimum **95% measured precision** on independently reviewed
examples before extracted mandatory requirements may cause candidate exclusion.
This is mandatory-classification precision, not the entity model's confidence
threshold and not a universal correctness guarantee. Unknown/conflicting context
still cannot cause exclusion. The user also selected minimum **80% measured recall** for mandatory
classification. Minimum sample counts, confidence threshold and field-level span
quality targets remain pending. Review labels independently
of source weak labels and GLiNER predictions; report sample counts and PT/EN
results alongside the combined 80% Portuguese / 20% English evaluation mix.
