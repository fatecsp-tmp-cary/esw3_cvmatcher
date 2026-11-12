# ADR-012: Issue completion, request budgets and reviewed evaluation

- **Status:** Accepted
- **Date:** 2026-11-12
- **Authority:** User interview while completing the issue-linked replacement PRs.
- **Supersedes:** Pending language/employment mappings, request processing budgets,
  sample minimums, evaluation partition/targets and deployment acceptance scope.
  Existing model-quality gates, privacy rules and immutable API remain in force.

## Context

The replacement PR stack must meet each associated issue's current acceptance
criteria. Earlier collection-cap and authentication checklists conflict with
accepted ADR-008/009/010/011. Historical implementation tests do not establish
human review or passing model quality. The original integration draft #164 and
older model draft #94 remain open as reference-only drafts, not merge candidates.

## Decision

Use CEFR A1–C2 and explicit Portuguese/English aliases for languages. Preserve
unknown/ambiguous levels as unknown. Employment categories are CLT, PJ, internship,
apprenticeship, temporary and freelance; never conflate these categories or infer
preferences from past employers. Supporting representations stay outside fixed
canonical Job/public API fields. Structured dimensions have equal weights when
both sides have comparable evidence; absent/unknown dimensions are omitted from
the denominator. Experience/education keep their accepted semantic aggregation.
All newly introduced exclusions remain disabled until user review: even known
incompatibilities affect scores only. Missing evidence never causes exclusion.

Allow one active matching request per API process, without a waiting queue.
Excess concurrency returns a privacy-safe 503. Apply a 30-second cooperative
processing deadline, checked between steps and inference batches; a native
inference call may finish before cancellation takes effect. Release the slot
only when processing unwinds. No curriculum field/body/collection cap is added.
Keep the distinct PostgreSQL-coordinated rolling 60/minute global admission limit.

The user will review the blind examples. Minimum corpus: 40 Portuguese and
10 English independently human-reviewed cases. Freeze 20 PT + 5 EN for calibration
and 20 PT + 5 EN for held-out evaluation before labels are used for tuning.
Do not select thresholds using held-out outcomes. Report counts/undefined metrics
and require positive support; absent support is not a pass. Extracted field/span
precision must reach 90% and recall 80%, separately for each language. Existing
mandatory-classification gates remain precision 95% and recall 80%. Semantic
role-matching acceptance is AUC at least 0.90 and accuracy at least 80%, separately
for each language, at a versioned cutoff frozen before held-out evaluation.
These are acceptance targets, not claims of passing measurements or final blended
ranking calibration. Keep actual annotations and measured evidence distinct.

Deployment issue #124 covers local pre-production configuration and recovery.
Track external HTTPS/provider acceptance separately (#150); no production
rollout, new reverse-proxy service or external deployment is authorized.

## Alternatives

Adding authentication or restoring old collection caps would contradict accepted
user decisions. Mapping ambiguous proficiency or inferred employment preferences
would fabricate evidence. Unbounded concurrency/deadlines would leave #151 open;
a strict native-call timeout cannot be claimed by cooperative checkpoints.
Expanding to 200 PT/50 EN was offered; the user retained 40 PT/10 EN and selected
a half calibration/half held-out split. Keeping all 50 held out was offered.
Bundled Caddy or a host Nginx reference was offered; external HTTPS was deferred.

## Consequences

Update current issue checklists without rewriting historical ADRs. Each replacement draft names its intended closing issue using the requested
closure keyword. Keep drafts with unpassed acceptance gates explicitly blocked;
a closure keyword is intent for a future accepted merge, not current completion. Human annotations and passing held-out
metrics remain necessary external evidence; an accepted protocol is not release
approval. The small held-out set limits statistical confidence. Larger samples
may be added while preserving the frozen evaluation split and provenance.
