# Semantic scoring policy

Authority: [ADR-008](../architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md)
and the implementation interview on 2026-11-11. This records policy decisions;
it does not claim production scoring or calibration is complete.

## Confirmed starting policy

- When both sections have evidence, combine the selected-experience score with
  the best education score using **80% experience / 20% education**.
- Validate these starting weights on reviewed examples before release. This is
  not evidence that the coefficients are calibrated or release-approved.
- Normalize over available sections: experience alone receives its full component
  score; education alone receives its full component score. Both absent yields zero.
- Retain ADR-008 selection by semantic similarity before recency weighting, its
  recency/tie ordering and the existing final textual/semantic/structured blend.
- The interview selected modest recency weighting, with the newest selected
  experience receiving up to 1.5 times the oldest's weight. Use weights
  **1.5, 1.25, 1.0** for distinct recency groups from newest to oldest; equal
  recency gets equal weight. With one/two distinct groups, use the first one/two
  weights. Selection still takes the three highest semantic scores first.
- The deterministic aggregation primitive is implemented in
  `src/matching/semantic.py`; its inputs must already be calibrated per-entry
  scores in [0,100]. It does not implement inference, calibration or API wiring.
  Its provisional policy version is `semantic-aggregation-v1-provisional`.

## Performance target

The user selected a five-second warm CPU response target for `POST /matches`.
The initial reference workload is 10 experiences, 5 education entries,
10,000 active jobs, limit=10 and one request at a time. Measure complete request
latency, with models already loaded, and report the distribution and failures;
do not silently redefine this as a component-only or percentile-only target.
This benchmark does not introduce public collection caps or guarantee latency
for every accepted request size. No performance result has been measured yet.

## Evaluation language mix

The user selected **80% Portuguese / 20% English** examples for model evaluation.
Report per-language results as well as the combined result so a language-specific
failure is visible. Both languages remain supported; this mix is not a geographic
eligibility rule.

## Pending interview decisions

- Similarity calibration and reviewed ranking examples/release thresholds.
- Model/revision selection and runtime/quality tradeoffs.

Implementation status remains in [MVP tasks](../../specs/feature-001-mvp/tasks.md).
