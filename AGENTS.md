# Project documentation guide

This file is the entry point for project documentation. Read it before changing
requirements, architecture, implementation plans, task status, or project docs.

## Authority and scope

- `docs/product/` governs product purpose, scope, and vocabulary.
- `docs/architecture/` governs architecture and invariants. Accepted decisions
  are recorded in `docs/architecture/decisions/`; supersede them with a new ADR,
  preserving the old record.
- `specs/feature-*/` governs feature behavior, acceptance, plan, and task status.
- `docs/quality/definition-of-done.md` governs completion and verification.
- `README.md` and `CONTRIBUTING.md` are contributor-facing entry documents and
  must link to the governing documents rather than duplicate them.
- `docs/data/` and `docs/match/` contain supporting technical material. Keep
  it consistent with the governing docs.
- `docs/reports/` is historical record only; it is not an enforced source of
  current requirements.

If documents conflict, do not silently choose an interpretation. Record the
conflict as an unresolved clarification in the relevant feature spec and task
list. Ask for a decision when implementation depends on it.

## Scope boundaries

Do not expand product scope, change an accepted decision, or alter an
architectural invariant without an explicit decision recorded in the docs.
Never implement a major architectural change without the user's explicit
approval. Before proceeding, present its proposal, rationale, alternatives, and
impact. After approval, record the decision and update affected docs and tasks.

## Workflow

For a change, identify affected product, architecture, feature, quality, and
supporting documents. Update them in the same change as the requirement,
architecture, implementation plan, or task-status change. Keep task status
factual and distinguish implemented behavior from planned behavior. Record
significant architecture decisions as ADRs with context, alternatives, rationale,
consequences, and status; accepted decisions are superseded, not rewritten.

## Verification

Before completing a documentation change, check internal links and references,
ensure each requirement has a clear authority, reconcile statements with the
codebase, and identify unresolved conflicts without resolving them implicitly.
For implementation work, use the feature acceptance criteria and Definition of
Done; document relevant tests, documentation updates, and verification results.
