# Issue #116 extraction correction — 2026-11-14

Authority: [ADR-014](../architecture/decisions/ADR-014-extraction-context-and-approximate-evidence.md).
Implementation/review owner: [PR #170](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/pull/170).
Evaluation packets, frozen configurations, original/final calibration, regression
predictions and case errors are maintained by
[PR #178](https://github.com/fatecsp-tmp-cary/esw3_cvmatcher/pull/178).

Clause-local classification, strongest occurrence projection, retained null
negation/conflict evidence, smallest meaningful Unicode spans, explicit section
fallback/background selection, dedicated entity labels, exact alias supplementation
and conservative one-edit typo support are implemented. Public API/canonical Job
and candidate request-scoped privacy remain unchanged. Semantic-only canonical
merging is disabled after the approved collision probe failed to separate pairs.

Verification: 118 focused extraction unit tests; 564 owning-branch full unit/API/
PostgreSQL tests; combined acceptance tree 742 tests (external CPU benchmark
excluded). Ruff lint/format and extraction-only mypy (9 files) pass here; full
mypy passes on the combined tree (68 files). This older owning branch retains a
pre-existing full-mypy annotation error at `src/matching/textual.py:12`; it was
not silently reported as passing or changed outside scope. Changed doc link
paths were checked. No model downloads/live sources are needed by ordinary CI.

Frozen extraction version: `gliner-job-v1-10f349187d105fe9764c7dc2`.
Calibration anchors: zero 0.67, full 1.0; role cutoff 50. Production keeps its
provisional semantic calibration; the fitted artifact is evaluation evidence.
All results below concern the semantic component, not final blended retrieval.

| Measurement | Language | Span P/R | Mandatory P/R | Role AUC | Accuracy |
|---|---|---|---|---|---|
| Calibration | PT (20) | 100% / 100% | 100% / 100% | 0.919 | 80% |
| Calibration | EN (5) | 100% / 100% | 100% / 100% | 1.000 | 100% |
| Former-held-out regression | PT (20) | 100% / 86.5% | 100% / 77.8% | 1.000 | 95% |
| Former-held-out regression | EN (5) | 100% / 100% | 100% / 100% | 1.000 | 100% |

The first correction's failed calibration is retained. It exposed cue-only
false entities and missed explicit credentials; the revised implementation was
fitted/validated on calibration only before the final freeze. No changes were
made after examining the corrected former-held-out predictions.

**Not release acceptance:** the old held-out inputs informed diagnosis, and
updated labels are user-authorized policy adjudications, not a new independent
human review. PT mandatory recall still fails 80%; extraction misses include
recruitment and automated-testing concepts, and the Python-developer/nurse role
error remains. EN has only three mandatory regression predictions. Fresh blind
review and any future mandatory sample minimum remain pending. All hard
exclusions remain disabled; no merge, deployment or release approval is granted.
