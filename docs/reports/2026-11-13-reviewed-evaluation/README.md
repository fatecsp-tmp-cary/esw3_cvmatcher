# Human-reviewed model evaluation evidence

Source application: `1139ada96caf4ede262c3a26e7c2e7cb4af97478`. [Isolated evaluation run](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/actions/runs/43527436908); runner commit `9b22782b7399a8da9fc9d88f5b8f5e6e12381a68`.

## Protocol and provenance

All 50 human annotations passed source-hash, unchanged-input, exact Unicode span, reviewer and frozen partition validation. The user explicitly confirmed the remaining uncertainty notes as final adjudications; derived copies preserve them as rationale. Originals remain unchanged.

Each partition contains 20 Portuguese and 5 English cases. Only calibration labels selected the similarity anchor. Extraction settings were unchanged. The configuration was written and hashed before held-out inference; held-out labels did not select parameters. The small synthetic sample limits generalization and precision of these estimates.

Frozen similarity version: `human-calibration-v1-932d24279f9a`; zero anchor **0.67**, full anchor **1.0**, classification cutoff **50**. Frozen at `2026-11-13T23:30:25.567663+00:00`.

Calibration searched 91 zero anchors from 0.00 through 0.90, with full anchor 1.0. Selection maximized mean PT/EN accuracy, then minimum language accuracy, then closeness to the previous 0.5 anchor. See protocol, search and raw-score artifacts.

## Calibration results

| Language | Cases | Span precision | Span recall | Mandatory precision | Mandatory recall | Role AUC | Role accuracy | Span / mandatory / role gates |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| PT | 20 | 71.8% | 84.8% | 25.0% | 5.3% | 0.979 | 85.0% | FAIL / FAIL / PASS |
| EN | 5 | 80.0% | 88.9% | 50.0% | 33.3% | 1.000 | 100.0% | FAIL / FAIL / PASS |

## Heldout results

| Language | Cases | Span precision | Span recall | Mandatory precision | Mandatory recall | Role AUC | Role accuracy | Span / mandatory / role gates |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| PT | 20 | 74.1% | 55.6% | undefined | 0.0% | 0.941 | 90.0% | FAIL / FAIL / PASS |
| EN | 5 | 12.5% | 62.5% | undefined | 0.0% | 0.750 | 80.0% | FAIL / FAIL / FAIL |

## Held-out support

- PT held-out support: 17 relevant / 3 irrelevant cases.
- EN held-out support: 4 relevant / 1 irrelevant cases.

## Acceptance status

Held-out combined targets met: **False**.

Targets, separately per language: span precision ≥90% / recall ≥80%; mandatory precision ≥95% / recall ≥80%; semantic role AUC ≥0.90 and accuracy ≥80%. Undefined metrics and missing positive support do not pass.

**Human release approval remains pending. All new hard exclusions remain disabled.** These semantic measurements evaluate the per-pair semantic component; they do not calibrate complete retrieval, the blended ranking, or probability of employment. No model/threshold changes were made after viewing held-out results.

## Case-level evidence

`heldout-case-errors.json` records every held-out case, its frozen score, expected role, exact missing/extra spans and class-sensitive differences. It includes correct cases for comparison. `heldout-predictions.json` and `heldout-report.json` preserve the complete machine-readable observations.

Any model changes based on these held-out errors require a new independent evaluation protocol and data. A rerun must not silently overwrite these observations.

## Files

- `frozen-calibration.json`: parameters, source/gold/protocol hashes, model versions and freeze timestamp.
- `calibration-search.json`, `calibration-raw.json`: calibration candidates and entry cosine observations.
- `calibration-report.json`, `heldout-report.json`: per-language counts, metrics and gates.
- `calibration-predictions.json`, `heldout-predictions.json`: full predictions.
- `installed-packages.txt`, model manifests and `review_evidence.py`: reproduction evidence.
- `sha256.json`: hashes of the delivered evidence files.
