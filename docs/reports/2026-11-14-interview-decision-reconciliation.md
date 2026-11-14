# Interview decision reconciliation — 2026-11-14

This documentation change records the user's decisions and reconciles identifiers.
It does not implement the newly accepted behavior or approve a release/merge.

| Record | Owning review/work | Accepted policy | Implementation status |
|---|---|---|---|
| [ADR-018](../architecture/decisions/ADR-018-extraction-context-and-approximate-evidence.md) | #116 / PR #170 | Existing extraction policy; identifier reconciled from duplicate ADR-014 | Existing correction preserved; no version/calibration change |
| [ADR-019](../architecture/decisions/ADR-019-title-first-job-evidence-and-displayed-skills.md) | #196 / PR #197 | Title > usable label > named body; restrictive title ordering; exact affirmative non-conflicting displayed extraction skills | Current draft differs; correction/tests pending |
| [ADR-020](../architecture/decisions/ADR-020-three-snapshot-stale-expiration.md) | #145, extending #186 / PR #187 | Three qualifying absence snapshots including the initial STALE transition; no age threshold | Supporting counters/expiration/tests pending |
| [ADR-021](../architecture/decisions/ADR-021-mandatory-coverage-score-only.md) | #120 / PR #173 | REQUIRED-only: all below three, otherwise max(3, ceil(0.70*N)); exact/approved aliases only | Coverage implementation pending; no new score weight or exclusion |
| [ADR-022](../architecture/decisions/ADR-022-bilingual-ascii-search-and-fuzzy-fallback.md) | #147/#159 / PR #172 and downstream retrieval | Separate lowercase ASCII projection, PT/EN stemming, fuzzy fill-only fallback | Representation/index/retrieval implementation and measurement pending |
| [ADR-023](../architecture/decisions/ADR-023-deferred-external-deployment-and-second-source.md) | #150 / PR #177; #127/#128 | External deployment and second-source research/selection deferred | No external provider/source/deployment selected |

ADR-014 remains the existing APiBR availability decision; ADR-015/016 remain the
accepted source-absence/inactive-result decisions. ADR-017 remains its original
proposal, superseded for field/display rules by ADR-019. The old extraction ADR-014
file is a historical redirect to ADR-018. Frozen reports, code snapshots, machine
policy identifiers and original reviewed labels retain their exact bytes.

Seniority title ordering is INTERN < JUNIOR < MID < SENIOR < SPECIALIST/COORDINATOR;
first occurrence wins specialist/coordinator ties. Work-arrangement order is
REMOTE < HYBRID < ON_SITE. A conflicting label set may resolve through a checked
body option when the title supplies nothing; an ambiguous label never blocks a
usable title. Stored canonical fields/API shape and candidate privacy stay fixed.

Scoring-only coverage is distinct from evaluation sample size. Additional minimum
gold/predicted mandatory mention counts remain deferred while exclusions are off.
Independent post-correction held-out review and the failed PT mandatory recall gate
remain outstanding. No previous measurement proves these new policies implemented.

Upstream documentation commits are carried through the review stack with ordinary
fast-forward branch updates. Later branches also inherit the previously published
extraction correction and evaluation evidence from #170/#178; this change introduces
no new production implementation of ADR-019 through ADR-022. The test append
conflicts were reconciled by retaining both existing regression groups.
