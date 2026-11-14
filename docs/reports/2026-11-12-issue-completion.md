# Issue-linked draft completion evidence — 2026-11-12

This historical report records the ADR-012/013 completion pass on replacement
PRs #165–#179. Governing behavior remains in the feature spec/acceptance and
accepted decisions. #94/#164 remain open reference-only drafts. No merge,
production deployment or human quality approval occurred.

## Implemented and verified

- Conservative CEFR/PT/EN and separate employment mappings; available comparable
  structured dimensions receive equal weights. Unknown values are omitted, past
  employers never imply preferences, and new hard exclusions remain disabled.
- Explicit contextual requirement classes and idempotent canonical taxonomy/alias
  projection into JobSkill/JobRequirement, preserving curated taxonomy and job hash.
- One execution per API process, privacy-safe busy 503, 30-second cooperative
  deadline, disconnect cancellation, and fixed-outcome timing without CV content.
- Explicit SNAPSHOT mode uses healthy equal before/after count/timestamp, exact
  distinct current-scan IDs, terminal empty page and zero failures/rejections/
  duplicates. Failed health transports roll back the poll. No absence expiry.
- Frozen blind review packets: 20 PT + 5 EN calibration, 20 PT + 5 EN held out;
  provenance/span validation and separate per-language gates reject undefined
  metrics. All actual human annotations and approvals remain pending.

Final isolated database suite: **658 passed, 1 external test deselected**.
The earlier actual E5 CPU reference passed at **3.548 / 4.558 / 3.524 s**
for 10 experience entries, 5 education entries, 10,000 ACTIVE jobs, limit 10,
three sequential warm requests, one CPU inference thread. This synthetic,
homogeneous corpus establishes neither general latency nor model quality.
[CPU artifact](2026-11-12-issue-completion-cpu.json).

Ruff lint/format, mypy (66 source files), dependency input/hash consistency and
10 dependency-checker tests passed. New/changed unit/API tests were also checked
at each owning stack step; PostgreSQL integration used the final isolated tree.
GitHub CI is a separate current-head check on each published draft. Initial
intermediate checks exposed missing torch/numpy because the shared hashed
inference-dependency installer was introduced only at the final CI step. Move
that installer into the extraction/dependency PR before embedding tests appear;
retain the full CI expansion in #179. The final application source is unchanged
by this ordering correction. A subsequent scoring audit omitted the skills
dimension when the candidate supplies no explicit competencies or recognized
skill mentions; a language-only curriculum no longer receives an invented zero
skills score. Explicit nonmatching skill evidence remains comparable. The new
boundary regression is included in the final 658-test count.

The actual offline local Compose/recovery drill passed, including clean migrations,
synthetic SNAPSHOT ingestion, GLiNER/E5 worker, deterministic REST, database/API
replacement and restoration into a separate empty project. Taxonomy state and
qualified snapshot evidence survived recovery. Its image predates the final
helper/scoring/rollback refinements; the final source was separately verified
by the complete database suite and actual CPU run. Keep this scope explicit.
[Compose artifact](2026-11-12-issue-completion-compose.json).

## Final scoring-version CPU observations

The updated structured policy is versioned as
`explicit-cefr-employment-equal-available-v2`. Its first CPU run measured
**3.349 / 3.685 / 20.718 s** and **failed** the five-second reference target.
[Failed observation](2026-11-12-issue-completion-cpu-outlier.json).
A second run of the same source/model/workload measured
**3.514 / 3.398 / 3.484 s** and passed the specified three-request reference.
[Repeat observation](2026-11-12-issue-completion-cpu-repeat.json).
The outlier's cause is unestablished; retain both observations. A successful
repeat does not erase the failure or establish stable latency/capacity. No
performance target or workload was relaxed, and no quality gate was passed.

## Remaining acceptance evidence

The user must independently label the blind packets. Calibration may use only
its frozen 25 cases; freeze its version before held-out evaluation. Span gates
are precision 90%/recall 80%, mandatory classification 95%/80%, semantic role
AUC 0.90/accuracy 80%, separately for each language with positive support.
No accepted protocol, synthetic test oracle or earlier agent labels count as a
passing human evaluation. #116/#120 drafts remain blocked on this evidence.

Local pre-production packaging is the accepted #124 scope. External HTTPS and
provider capabilities remain #150. Source rights/retention (#134), independent
availability verification and absence policy (#145) are separate outstanding
work; count attestation proves none of them.
