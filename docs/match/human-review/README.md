# Blind human review packet

Review [cases.json](cases.json): 50 synthetic examples, 40 Portuguese and 10 English.
All source job/candidate inputs are preserved. Existing agent labels, explanatory
tags and model predictions are omitted. Every review starts pending. The source
fixture path and SHA-256 identify the exact inputs; do not consult its labels or
model reports before independently annotating the packet.

## Annotating a case

Edit only its `review` object. Keep the original IDs, language, inputs and source
hash unchanged. Record the actual reviewer name or stable reviewer identifier,
ISO-8601 `reviewed_at`, and a short independent rationale. No real candidate data
should be added: these inputs are synthetic.

- Set `role_relation` to `relevant` or `irrelevant` based on the candidate's
  professional/education evidence for this job. If the decision is unclear,
  leave it null, explain `uncertainties`, and keep status `needs_adjudication`.
  Location is never geographic eligibility evidence; compatibility is not a
  probability of employment.
- Set `requirements` to all explicit requirement mentions in `job.description`.
  Use `[]` only after affirmatively finding none; null means unreviewed.
  Each item has `text`, `start`, `end`, `requirement_class`. Offsets are zero-based
  Unicode code-point positions in that exact description, end-exclusive:
  `description[start:end]` must equal `text`. Do not count UTF-8 bytes or UTF-16
  code units, strip whitespace, or normalize the text before locating spans.
- Use `REQUIRED` only for explicit mandatory language, `PREFERRED` for explicitly
  desirable evidence, `NICE_TO_HAVE` for optional added value, and JSON null for
  an unclassified mention. A mention, entity type or confidence alone never
  makes a skill mandatory. Put conflicting/ambiguous evidence in `uncertainties`.
- Mark `status` as `reviewed` only once all annotations are complete and checked.
  Use `needs_adjudication` for disagreements or unresolved interpretations. A
  second independent reviewer should record disagreements and their resolution
  in a separate reviewed copy or review record, without silently overwriting them.

For an offset check, copy only a synthetic case into a local Python interpreter
and verify `description[start:end] == text`. Preserve accented characters and
newlines exactly. Do not paste real CVs into this packet.

## Returning and using annotations

Return the edited packet for validation. Keep the original packet and a separate
reviewed copy so the review history remains available. Do not flip top-level
`human_reviewed` or `release_quality_approved`: the primary must validate every
case, source hash, reviewer record, span and unresolved disagreement before
creating a versioned gold fixture. Nothing in this packet automatically enables
mandatory exclusions or changes production models/calibration.

The existing set is small and synthetic. Human annotation alone establishes
neither representative coverage nor sample sufficiency. Approve sample sizes,
PT/EN coverage, calibration/held-out split and quality criteria separately before
fitting thresholds; retain a held-out evaluation set. The accepted mandatory
exclusion targets remain at least 95% precision and 80% recall on independently
reviewed examples. Current extraction does not meet that gate, and mandatory
model exclusions remain disabled. See [evaluation provenance](../evaluation-fixtures.md)
and [acceptance](../../../specs/feature-001-mvp/acceptance.md).
