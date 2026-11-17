# Semantic scoring policy

Authority: [ADR-008](../architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md)
and the implementation interview on 2026-11-11. This records policy decisions;
the deterministic scoring primitives and request-scoped matching pipeline are
implemented in this branch and composed by the production API in #175.
Calibration remains provisional and release approval remains disabled.

## Confirmed starting policy

- When both sections have evidence, combine the selected-experience score with
  the best education score using **80% experience / 20% education**.
- Validate these starting weights on reviewed examples before release. This is
  not evidence that the coefficients are calibrated or release-approved.
- Normalize over available sections: experience alone receives its full component
  score; education alone receives its full component score. Both absent yields zero.
  Normalize configured weights over available sections only, including extreme
  finite ratios; an absent section must never underflow available evidence.
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
  scores in [0,100]. `src/matching/pipeline.py` embeds and scores each available
  experience/education entry and combines current textual/semantic candidates.
  When both sections are absent it performs no semantic encoding or retrieval;
  competencies/projects/languages may still retrieve actual textual evidence,
  but every returned job must also have current successful extraction and embedding
  provenance under [ADR-024](../architecture/decisions/ADR-024-all-result-extraction-and-embedding-readiness.md)
  and [ADR-027](../architecture/decisions/ADR-027-bidirectional-scoring-dual-vectors-seniority-filter.md),
  including both the full job vector (`jobs.embedding`) and the internal job-core
  vector (`job_embeddings.core_embedding`, combined per entry via
  `max(core, 0.65*core + 0.35*full)`).
  This job-readiness gate does not invent candidate semantic evidence.
  Production API composition in `src/api/runtime.py` is implemented in #175.
  Per-entry cosine calibration is explicit and provisional.
  Its provisional policy version is `semantic-aggregation-v3-provisional`; v3
  adds bidirectional candidate-summary alignment (`summary_weight = 0.25` against
  `core_embedding`) and a gentle CV-breadth coherence factor (`0.8 + 0.2*ratio`)
  under [ADR-027](../architecture/decisions/ADR-027-bidirectional-scoring-dual-vectors-seniority-filter.md),
  paired with `ts_rank_cd` saturation (`flag 32`), query-term length
  normalization, and `focused_candidate_query_text` for FTS.
  The default 80/20 weights, recency weights and final blend are unchanged.
- Retrieval-pool limits must be positive integer counts; booleans, fractions and
  nonfinite values are rejected before reaching SQL `LIMIT`.

## Performance target

The user selected a five-second warm CPU response target for `POST /matches`.
The initial reference workload is 10 experiences, 5 education entries,
10,000 active jobs, limit=10 and one request at a time. Measure complete request
latency, with models already loaded, and report the distribution and failures;
do not silently redefine this as a component-only or percentile-only target.
This benchmark does not introduce public collection caps or guarantee latency
for every accepted request size. Historical evidence from the original integration
on 2026-11-12 recorded three complete warm requests at 2.157, 2.111 and 2.133
seconds with one CPU inference thread. Jobs were homogeneous synthetic records
and entries repeated. That measurement was not rerun at this branch head and does
not validate the revised extraction/embedding policies or this scoring version.
The opt-in `tests/e2e/test_cpu_reference.py` and its implementation report arrive
in stack PR #178; they are absent at this step. Current-head end-to-end performance
acceptance remains pending.

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
>=80% are required separately per language; these targets remain unmeasured on
human-reviewed held-out gold. Existing agent labels are not substituted for it.

Seniority comparison uses the [ADR-027](../architecture/decisions/ADR-027-bidirectional-scoring-dual-vectors-seniority-filter.md)
symmetric ladder (`INTERN(0) < JUNIOR(1) < MID(2) < SENIOR(3) < SPECIALIST(4) = COORDINATOR(4)`).
Candidate seniority uses explicit title markers in the already selected relevant
experience entries (frozen semantic cutoff 50), taking `max(explicit, SENIOR)`
when relevant tenure reaches `>= 60` months, and falling back conservatively to
tenure when unmarked (`< 12` months total or `0` experiences -> `JUNIOR`;
`>= 60` months relevant -> `SENIOR`). Ongoing experiences use one request-scoped
UTC date (`as_of_date`, injectable in tests) so identical inputs within a day/pin
stay deterministic. When both sides are known, a gap `>= 2` hard-filters the job
symmetrically (with bounded pool refills if needed); a gap of `1` scores `40.0`
with a `0.85` score multiplier. Unknown seniority never filters. All other
exclusions remain disabled until user review.

A job skill list alone does not establish candidate skill evidence. When no
explicit competencies or recognized skill mentions exist in the curriculum, omit
the skills dimension rather than scoring unknown knowledge as zero. Explicit
nonmatching skill evidence remains a comparable score-only dimension.

## Accepted mandatory coverage and bidirectional skills

[ADR-021](../architecture/decisions/ADR-021-mandatory-coverage-score-only.md)
and [ADR-027](../architecture/decisions/ADR-027-bidirectional-scoring-dual-vectors-seniority-filter.md)
govern tiered bidirectional skill scoring in `src/domain/requirements.py`
(`bidirectional-tiered-adr021-v3`): `REQUIRED` (weight `1.0`) and `ADR-021`
exact-evidence mandatory coverage (`N=1,2 -> N; N>=3 -> max(3, ceil(0.70*N))`),
`PREFERRED` (`0.4`), `NICE_TO_HAVE` (`0.15`), Bayesian sparse-job smoothing
toward neutral `0.5` (`strength = 2.5`), and clamped Candidate→Job core-skill
precision (`sqrt(matched ∩ core / min(core, 15))` over the single core
projection of competencies, projects, and the 3 most recent experiences)
combined via $F_{1.5}$. This remains score-only with no skill exclusion.
