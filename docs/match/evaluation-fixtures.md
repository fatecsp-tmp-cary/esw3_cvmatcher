# Independent synthetic evaluation fixtures

[Fixture](../../tests/fixtures/matching/reviewed_cases.json) schema 1.0 contains
50 synthetic cases, exactly 40 Portuguese and 10 English. An independent
reviewer agent authored and interpreted these labels before observing any model
outputs. No inference, model reports, real candidate data, or external datasets
were read to derive labels. These are **agent-reviewed synthetic** examples;
they are not human-reviewed release gold and establish no measured release quality.

Each stable language-prefixed ID has job title, description and positively stated
skills, candidate experience/education/competencies without identity, a binary
role relation, rationale and expected requirement spans. Professions, explicit
requirements, preferences, bonuses, negation, uncertainty, unresolved conflicts,
seniority, empty evidence and long descriptions are covered. Empty candidate
evidence is labeled irrelevant (no evidence of role relevance).

Offsets are zero-based Python Unicode character offsets in `job.description`,
with exclusive end. The text slice must equal `text`. Labels are REQUIRED,
PREFERRED, NICE_TO_HAVE, or JSON null. Optional/bonus wording maps to NICE_TO_HAVE;
explicit desirable/preferred wording maps to PREFERRED. Null means the mention
does not establish requirement strength, including negation, uncertainty and
unresolved contradictions. For contradictory repeated concepts the first mention
is the annotation anchor; do not interpret the first clause without its context.
The corpus annotates listed requirement concepts, not every possible entity.
Structured skills list only positively stated concepts. Locations never establish
eligibility. Role relevance concerns professional alignment, not a claim that all
mandatory requirements are satisfied. Paired related/unrelated professions make
this distinction testable.

## Offline evaluator

Run from repository root using the existing Python environment:

```sh
python scripts/evaluation/evaluate.py --predictions /path/to/predictions.json
```

An optional `--fixtures` overrides the default fixture path. External predictions
must use this shape (the illustrative span matches pt-001):

```json
{
  "schema_version": "1.0",
  "predictions": [
    {
      "id": "pt-001",
      "requirements": [
        {"text": "Python", "start": 0, "end": 6, "requirement_class": "REQUIRED"}
      ],
      "role_score": 85
    }
  ]
}
```

Scores must be finite in [0,100]. Unknown/duplicate IDs, duplicate spans,
incorrect offsets and vocabulary fail validation. Missing cases are allowed and
explicitly listed. Each provided case must supply both fields; an empty
requirements list is an explicit empty extraction. No prediction means empty
extraction for recall and incorrect role classification, including irrelevant
cases. Missing predictions cannot satisfy the synthetic mandatory gate.

JSON stdout reports micro precision/recall and counts globally and by language.
Exact extraction matches `(start, end, requirement_class)`, including null.
Mandatory metrics restrict both sides to REQUIRED; wrong class is a miss and,
when applicable, a false positive. Undefined precision/recall is JSON null.
Ranking quality is pairwise AUC over observed relevant/irrelevant case scores,
with ties worth 0.5, explicit observed pair counts and completeness. This measures
role separation across independent pairs, not per-candidate retrieval NDCG.
Missing cases are excluded from observed AUC but count against all-case role
accuracy (fixed score cutoff 50). Never present partial AUC as complete quality.

The synthetic mandatory gate requires complete prediction coverage, precision
>=95% and recall >=80%, separately for each reported group. These are the
[acceptance targets](../../specs/feature-001-mvp/acceptance.md), not a claim they
have passed. Minimum release sample sizes, calibration and human review remain
unresolved. The CLI exits 0 for a valid report regardless of gate result and 2
for invalid input. Primary owns model inference and scoring integration; this
change provides neither. External predictions should contain synthetic data only;
the CLI prints aggregate metrics and stable missing IDs, never candidate text.

Run fixture and evaluator regression checks:

```sh
python -m pytest --no-cov -q tests/unit/evaluation/test_fixture_contract.py
```

Oracle round-trip tests copy expected labels solely to verify metric plumbing;
they are not inference results or evidence of extraction/ranking quality. No
model packages, database or network are required. No product contract or
architecture changes are introduced; see [ADR-008](../architecture/decisions/ADR-008-extraction-contract-and-semantic-evidence.md).

## Actual offline model measurement (2026-11-12)

After independent labels were committed and reviewed, the primary ran pinned
GLiNER/E5 locally with no downloads. See the [aggregate report](../reports/2026-11-12-local-model-evaluation.json).
Semantic per-pair role AUC was 0.989 overall, 0.994 PT and 1.000 EN; role accuracy
at the provisional cutoff was 72%. This evaluates the semantic component, not
complete retrieval/final blended ranking. The small synthetic set is not a
human-reviewed release gold set or calibrated employment probability.

Exact span-plus-class precision/recall was 12.9%/16.5%; GLiNER emits unclassified
mentions, so these metrics must not be interpreted as a tuned requirement
classifier. Mandatory recall was zero, precision undefined, and all mandatory
gates failed. Mandatory exclusions therefore remain disabled. No threshold was
fit to these examples after observing their labels.

To repeat explicitly, with prepared caches and new output paths:

```sh
PYTHONPATH=. python scripts/evaluation/run_local.py --extraction-directory /path/to/prepared/gliner --predictions /path/to/new-synthetic-predictions.json --report /path/to/new-aggregate-report.json
```

Only synthetic fixture IDs, job spans and scalar scores are written; candidate
embeddings remain transient. Existing outputs are not overwritten.

## Human review preparation (2026-11-12)

At the user's request, a [blind human review packet](human-review/README.md)
contains the same 40 PT/10 EN synthetic inputs with source hash and pending
annotations. Existing agent labels, hint tags and model outputs are omitted.
It has not been human-reviewed and is not a release gold set; validation,
adjudication, sample sufficiency and held-out calibration decisions remain.

## Human-reviewed partition evaluation

ADR-012 fixes 20 PT/5 EN calibration cases and 20 PT/5 EN held-out cases.
The [blind review packets](human-review/README.md) and partition are frozen before
human annotations. `promote_review` validates complete independent labels without
automatically approving quality. With a validated gold fixture, the evaluator
supports `--partition calibration` or `--partition heldout`; predictions must
contain only that partition. `run_local.py` accepts the same options and uses the
same contextual span-classification policy as persisted extraction.

```sh
python scripts/evaluation/evaluate.py --fixtures /path/to/human-gold.json --partition heldout --predictions /path/to/heldout-predictions.json
```

The report separates class-agnostic exact `field_spans` from exact span-plus-class
and mandatory metrics. Accepted per-language targets are field precision 90% /
recall 80%, mandatory precision 95% / recall 80%, semantic role AUC 0.90 and role
accuracy 80% at the frozen cutoff 50. Missing predictions and undefined metrics
fail the relevant targets. Human review flags require per-case provenance; only
the held-out partition can report held-out targets met. Release approval remains
false regardless of a mathematical gate result. Freeze/version fitted calibration
using calibration cases only before held-out measurement; never fit to held-out
labels. The current packets are still unreviewed and no passing human quality
or fitted calibration is claimed.
