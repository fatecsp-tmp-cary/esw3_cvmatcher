# ADR-023: External deployment and second-source selection remain deferred

- **Status:** Accepted
- **Date:** 2026-11-14
- **Authority:** User interview following the extraction correction and branch decision audit.
- **Supersedes:** No accepted architecture; confirms ADR-010/012 local scope and defers optional expansion.
- **Implementation status:** Policy recorded; implementation and verification remain pending unless separately evidenced in feature tasks.

## Context

Local pre-production is the accepted scope. APiBR meets the MVP's one-source
minimum; no external provider/domain/budget or second source has been selected.

## Decision

Keep external deployment/provider selection and external HTTPS configuration
deferred. Continue within accepted local pre-production; do not infer permission
to provision, purchase, expose or deploy an external service. Keep second-source
research/selection and adapter implementation deferred for now. APiBR remains the
only selected source. No provider, budget, domain, new source or scraping scope
is approved. Existing source-permission verification obligations remain open.

## Alternatives and rationale

An external deployment proposal and immediate second-source research were
offered; the user chose deferral for both. Expanding infrastructure or ingestion
would add commitments before current source/matching acceptance is established.

## Consequences

#150 and #127/#128 remain deferred, not completed or cancelled. Existing local
Compose/recovery work and APiBR evidence/quality work can continue. Future external
exposure still requires HTTPS and existing privacy/database protections; deferral
is not permission to weaken them. Revisit scope explicitly before external
provisioning or a second-source implementation.
