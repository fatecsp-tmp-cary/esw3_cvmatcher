# ADR-024: Current extraction and embeddings for every returned job

- **Status:** Accepted
- **Date:** 2026-11-15
- **Authority:** User clarification during the PR #195 review.
- **Supersedes:** ADR-016's ambiguous readiness wording and the earlier allowance
  for extraction-ready textual results without a current job embedding.

## Context

ADR-016 required current extraction and embedding provenance for both groups,
but also said active matching stayed unchanged. The preceding active textual
path allowed an extraction-ready job without a vector. Issue #194 repeated the
unchanged active path while explicitly requiring vectors for inactive results.
The review recorded this conflict and asked the user to select the readiness rule.

## Decision

Every returned job, active or inactive, requires successful extraction for its
current content/configuration and a valid job embedding with current content,
model/policy and extraction provenance. Textual retrieval cannot bypass either
gate. Missing, stale, pending or failed processing withholds the job from results.

Keep active-first grouping, inactive completion, eligibility flags, scoring,
public schemas, privacy and geographic rules unchanged. Existing expired jobs
may be returned only while their already-produced extraction and vector remain
current; this decision does not authorize background processing of expired jobs.

## Alternatives and rationale

Allowing textual results without vectors only in the active group preserves the
old active path but creates different readiness guarantees. Allowing them in both
groups preserves lexical fallback but contradicts the selected all-result gate.
The user chose consistent current extraction and embedding readiness for every
returned job.

## Consequences

Fewer results may be available while processing is incomplete. Apply the same
readiness predicate at retrieval and final rechecks in both groups; retain the
existing partial active indexes. Add regressions for missing/stale/failed vectors
and extraction in each group. This is a readiness decision, not model-quality,
merge, deployment or release approval. Preserve ADR-016 as historical record.
