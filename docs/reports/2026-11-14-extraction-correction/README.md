# Extraction correction: frozen calibration and former-held-out regression

Implementation: [PR #170](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/pull/170),
commit `a137243`. Evaluation owner: [PR #178](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/pull/178).
Authority: [ADR-014](../../architecture/decisions/ADR-014-extraction-context-and-approximate-evidence.md).

**Release acceptance is not granted. All new hard exclusions remain disabled.**
The old held-out examples informed diagnosis; updating their labels cannot renew
independence. PT mandatory recall still fails the unchanged 80% target. These
results support a score-only correction and do not approve a merge or deployment.

## Inputs and provenance

The original reviewed source is retained as
[source-reviewed-gold.json](../../match/human-review/extraction-policy-v2/source-reviewed-gold.json).
The [updated gold](../../match/human-review/extraction-policy-v2/gold.json),
[calibration copy](../../match/human-review/extraction-policy-v2/calibration.json),
[former-held-out copy](../../match/human-review/extraction-policy-v2/heldout.json)
and [case-level changes](../../match/human-review/extraction-policy-v2/changes.json)
preserve all job/candidate inputs and original partition IDs. Sixteen cases have
explicit policy edits: retain negated entities as null; resolve diferencial to
PREFERRED; consolidate repeated concepts at their strongest actual occurrence;
and reconcile empty-evidence rationales with the user's revised irrelevant labels.
Hedge labels already agree with NICE_TO_HAVE. These are user-authorized policy
adjudications performed by the assistant, not a new independent per-case review.
No labels came from model outputs or the production classifier.

Historical failed human-reviewed measurement is preserved at
[the original report](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/blob/381a898bf4be319e2dff0364fa6fa22749cff65b/docs/reports/2026-11-13-reviewed-evaluation/README.md).
The original revised-role-label audit source is archived above with its hash.
Neither that report nor the user's edited workspace packets were overwritten.

## Measurement sequence

1. [Initial correction calibration](calibration/report.json) failed PT span
   precision (89.2%) and mandatory precision/recall (78.9%/78.9%). Its
   [predictions](calibration/predictions.json), [case errors](calibration/case-errors.json),
   scalar evidence, freeze and exact code snapshots are retained.
2. Calibration-only error analysis found cue-only false entities, generic
   seniority wrappers and missed explicit credential names. The revised policy
   excludes cue-only entities, trims grammatical wrappers and supplements local
   GLiNER detections with exact occurrences from the shared explicit vocabulary.
   Lexical source/confidence does not imply requirement strength. No semantic
   merging or new hard exclusion was enabled.
3. [Final calibration](calibration-v3/report.json) ran only the original 20 PT/5 EN
   calibration cases. The same predeclared 0.00–0.90 zero-anchor grid and fixed
   full=1.0/cutoff=50 were used; selection maximizes mean PT/EN accuracy, then
   minimum language accuracy, then closeness to zero=0.5. Extraction confidence
   remains 0.3. [All trials](calibration-v3/calibration-search.json) are retained.
4. The [final freeze](calibration-v3/frozen-calibration.json) pins extraction
   `gliner-job-v1-10f349187d105fe9764c7dc2`, anchors **0.67 → 1.0**, cutoff **50**,
   exact policy/model/artifact/gold/code hashes and timestamp. Weights are unchanged.
   Production's provisional similarity configuration was not replaced by this
   evaluation artifact. Independent review/rollout remains separate.
5. Only after that freeze, [former-held-out regression](former-heldout-regression/report.json)
   measured the updated old 20 PT/5 EN cases. No source, threshold, alias or
   calibration change followed inspection of those corrected predictions. The
   runner verifies the same extraction version, gold and code hashes before
   regression. This is regression/development evidence, not held-out acceptance.

## Separate language results

P/R denotes exact precision/recall. Span metrics ignore requirement class;
mandatory metrics require the exact span and REQUIRED class. Both phases have
complete prediction coverage with zero inference failures. Semantic results
measure per-pair E5 role separation, not full retrieval or final blended scores.

| Phase | Language / cases | Span P/R | Mandatory P/R | Mandatory TP / FP / FN | Semantic AUC | Role accuracy |
|---|---|---|---|---|---|---|
| Calibration | PT / 20 | 100% / 100% | 100% / 100% | 19 / 0 / 0 | 0.919 | 80% |
| Calibration | EN / 5 | 100% / 100% | 100% / 100% | 6 / 0 / 0 | 1.000 | 100% |
| Former-held-out regression | PT / 20 | 100% / 86.5% | 100% / **77.8%** | 14 / 0 / 4 | 1.000 | 95% |
| Former-held-out regression | EN / 5 | 100% / 100% | 100% / 100% | 3 / 0 / 0 | 1.000 | 100% |

ADR-012 numerical targets remain span P/R >=90%/80%, mandatory >=95%/80%, AUC
>=0.90 and accuracy >=80%, separately per language. Undefined metrics/absent
support fail. All calibration targets meet numerically on this small set. PT
mandatory regression recall fails; other regression numerical targets meet.
`release_quality_measured`, `heldout_targets_met` and `release_quality_approved`
remain false because this is no longer independent evidence. The original sample
minimum does not establish representative population quality; only three EN
mandatory regression predictions support that language's measured precision.
Future mandatory-mention minimums were explained and deferred with score-only use.

Remaining [regression case errors](former-heldout-regression/case-errors.json):
recruitment and automated-testing requirement misses, a publications miss, and
`pt-028` (Python developer versus nurse) above the role cutoff. Calibration role
errors also remain [case-by-case](calibration-v3/case-errors.json). None were
removed, relabeled to fit predictions, or used for post-freeze tuning.

## Semantic-equivalence diagnostic

The [raw cosine probe](semantic-equivalence.json) uses the pinned E5 model on
C/C#, C/R, Java/JavaScript, Ruby/Rails and PHP/WordPress, plus true aliases and
identity. Bare names and English/Portuguese context templates were tested with
query/query, passage/passage and both query/passage directions. No tested scalar
threshold rejects all distinct-language pairs while accepting both related pairs.
For bare query/query, Java/JavaScript is 0.924 versus Ruby/Rails 0.894. These are
cosines, not probabilities; related technologies are not canonical aliases.
The [probe source](semantic-probe.py.txt) is archived. Only explicit aliases can
establish canonical equivalence. Bounded one-edit matching is score-only support
and retains approximation provenance.

## Verification and reproduction

[Verification record](verification.json): 118 focused extraction unit tests,
564 owning-branch full tests and 742 combined unit/API/PostgreSQL/integration
checks, with the external CPU benchmark deselected. Ruff lint/format passes;
extraction mypy checks 9 modules and combined full mypy checks 68. Failed interim
test runs and the older owning branch's pre-existing FTS type-annotation failure
are recorded rather than counted as passes. This is not a new latency benchmark.

Serving weights/revisions are unchanged. The [artifact manifest](extraction-manifest.json)
records the revised policy and exact hashes; model files are not committed.
Inference remained offline on CPU/one thread. Existing SentencePiece byte-fallback
and generic tokenizer-regex warnings remain documented limitations; no unreviewed
model-specific tokenizer workaround was applied. A token-budget check warning on
rejected long windows is not evidence of a truncated serving chunk; bounded
coverage and exact-token-budget tests pass.

With the pinned environment and prepared extraction artifacts:

```sh
python -m scripts.evaluation.measure_extraction_policy --phase calibration \
  --fixtures docs/match/human-review/extraction-policy-v2/gold.json \
  --extraction-directory /path/to/prepared/extraction \
  --embedding-cache /path/to/huggingface/hub \
  --output-directory /path/to/new-calibration-output
```

The explicit `--phase regression --frozen /path/to/frozen-calibration.json` mode
uses the old held-out partition without fitting and cannot grant acceptance.
Outputs use exclusive creation. Per-case model/validation failures retain stable
IDs and fixed categories, not candidate text or exception strings. Only the
pre-existing synthetic fixture and scalar scores/detections are archived; real
candidate data and candidate embeddings are neither persisted nor logged.
Source snapshots are stored as `*.py.txt` under each calibration's `code/` tree
so historical code is not linted/executed as current production source. Their raw
bytes match each freeze's `code_hashes`; remove the final `.txt` when restoring
an isolated reproduction checkout. [SHA-256 inventory](sha256.json) covers this
bundle, excluding the inventory itself.

Fresh independently reviewed held-out evidence, approved support counts if
exclusions are ever proposed, and explicit release/merge decisions remain pending.
