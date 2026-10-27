# Definition of Done

## Per-change completion

A change is complete when its relevant acceptance criteria are met, the
implementation and documentation changes are reviewed, and relevant unit,
integration, API, and/or end-to-end tests are complete. Update the governing
requirements, architecture, acceptance criteria, plan, tasks, and supporting
docs when affected; check cross-references and consistency with code; and record
verification and limitations. Live-source tests are optional and must not be
required in CI. Apply the criteria relevant to the change rather than requiring
every change to satisfy the full MVP release gate below.

## MVP release gate

The MVP is complete when its acceptance criteria are met and the end-to-end
path works:

```text
Structured CV → CandidateProfile → job sources → normalized jobs → lifecycle
→ FTS + vector index → filters → textual + semantic matching → ranking → REST response
```

The MVP must accept structured CV JSON, implement at least one source, normalize
to the canonical `Job`, maintain source identity and content hashes, handle
source-specific lifecycle semantics and failures, expire/reactivate correctly,
exclude expired jobs from active retrieval, use FTS and local semantic search,
regenerate embeddings after content/model changes, and return deterministic
`[0,100]` compatibility scores with versioned algorithm/model and supporting
match information. Brazilian source priority does not permit geographic
eligibility filtering.

The fixed matching regression dataset and explicit
no-deduplication/no-geographic-filtering regressions are required for the MVP
release when those components exist. See
[acceptance](../../specs/feature-001-mvp/acceptance.md).
