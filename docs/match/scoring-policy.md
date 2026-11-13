# Semantic scoring policy

Authority: [ADR-008](../architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md)
and the implementation interview on 2026-11-11. This records policy decisions;
production scoring is wired, while calibration and release approval remain provisional.

## Confirmed starting policy

- When both sections have evidence, combine the selected-experience score with
  the best education score using **80% experience / 20% education**.
- Validate these starting weights on reviewed examples before release. This is
  not evidence that the coefficients are calibrated or release-approved.
- Normalize over available sections: experience alone receives its full component
  score; education alone receives its full component score. Both absent yields zero.
- Retain ADR-008 selection by semantic similarity before recency weighting, its
  recency/tie ordering and the existing final textual/semantic/structured blend.
  The final blend stays within [0,100], including floating-point rounding at
  the endpoints when configured weights sum to one within validation tolerance.
- The interview selected modest recency weighting, with the newest selected
  experience receiving up to 1.5 times the oldest's weight. Use weights
  **1.5, 1.25, 1.0** for distinct recency groups from newest to oldest; equal
  recency gets equal weight. With one/two distinct groups, use the first one/two
  weights. Selection still takes the three highest semantic scores first.
- The deterministic aggregation primitive is implemented in
  `src/matching/semantic.py`; its inputs must already be calibrated per-entry
  scores in [0,100]. Production inference and API wiring are provided by `src/matching/pipeline.py` and `src/api/runtime.py`. Per-entry cosine calibration is explicit and provisional.
  Its provisional policy version is `semantic-aggregation-v1-provisional`.

## Performance target

The user selected a five-second warm CPU response target for `POST /matches`.
The initial reference workload is 10 experiences, 5 education entries,
10,000 active jobs, limit=10 and one request at a time. Measure complete request
latency, with models already loaded, and report the distribution and failures;
do not silently redefine this as a component-only or percentile-only target.
This benchmark does not introduce public collection caps or guarantee latency
for every accepted request size. The opt-in offline reference passed on 2026-11-12: three complete warm requests took 2.157, 2.111 and 2.133 seconds with one CPU inference thread. Jobs were homogeneous synthetic records and entries repeated; this is a reference measurement, not general capacity or quality proof. See `tests/e2e/test_cpu_reference.py` and the current implementation validation report.

## Evaluation language mix

The user selected **80% Portuguese / 20% English** examples for model evaluation.
Report per-language results as well as the combined result so a language-specific
failure is visible. Both languages remain supported; this mix is not a geographic
eligibility rule.

## Remaining calibration and release work

- Similarity calibration and reviewed ranking examples/release thresholds.
- Pinned model/revision metadata is implemented in [local embeddings](local-embeddings.md) and [local GLiNER](../data/local-gliner.md); empirical quality tradeoffs remain under evaluation.

Implementation status remains in [MVP tasks](../../specs/feature-001-mvp/tasks.md).

## Reviewed acceptance policy

[ADR-012](../architecture/decisions/ADR-012-issue-completion-and-evaluation-policy.md)
sets conservative CEFR/employment mappings and equal weighting across available,
comparable structured dimensions. Unknown evidence contributes no invented
compatibility or exclusion. Employment is not inferred from past employers.
Experience/education weights above are unchanged. All new hard exclusions stay
disabled until user review. The human reviewer is the user; minimum 40 PT/10 EN
cases split 20 PT/5 EN calibration and 20 PT/5 EN held out. Freeze calibration and
score cutoff before held-out evaluation. Semantic role AUC >=0.90 and accuracy
>=80% are required separately per language; these targets were measured on human-reviewed held-out gold on 2026-11-13.
English semantic AUC and both extraction gates failed; see the
[evaluation evidence](../reports/2026-11-13-reviewed-evaluation/README.md). Existing agent labels are not substituted for it.

Seniority comparison uses explicit title markers only in the already selected
experience entries whose versioned semantic role score reaches the frozen relevance
cutoff 50. Unrelated career levels never establish job-specific seniority. Specialist
and coordinator tracks are not assigned an invented numeric ordering relative to
intern/junior/mid/senior; noncomparable tracks are omitted unless exactly matched.

A job skill list alone does not establish candidate skill evidence. When no
explicit competencies or recognized skill mentions exist in the curriculum, omit
the skills dimension rather than scoring unknown knowledge as zero. Explicit
nonmatching skill evidence remains a comparable score-only dimension.
