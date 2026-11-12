# ADR-014: APiBR listing presence is open-vacancy evidence

- **Status:** Accepted
- **Date:** 2026-11-12
- **Authority:** Tech lead decision after a local end-to-end run of the complete
  pipeline against the live source, with the evidence and alternatives below.
- **Supersedes:** Only the ADR-003 rule that an APiBR record without explicit
  state leaves a new job `DISCOVERED`. Partial-run, rollback, no-hidden-request,
  retention and absence rules in ADR-002/003/013 remain unchanged.

## Context

ADR-003 kept APiBR jobs without availability evidence outside active retrieval
until a verifier existed. A local run on 2026-11-12 ingested 729 live records:
none carried `state`, every job stayed `DISCOVERED`, and `POST /matches` returned
an empty list for real data. The source-to-match path required by the
[Definition of Done](../../quality/definition-of-done.md) therefore produced no
result with the selected MVP source.

Source evidence observed on 2026-11-12, with no source record retained:

- The published OpenAPI document describes `GET /vagas/api/v2/issues` as
  returning "a paginated list of open vacancies (GitHub issues)", and the API
  describes itself as aggregating open vacancies.
- The endpoint returns no `state` field and ignores a `state` query parameter.
- A random sample of 45 listed issues, each checked on GitHub, was open (45/45).

## Decision

Presence of a record in a successfully read APiBR listing response is open
evidence. A listed record normalizes to `ACTIVE`, and a successful observation
advances `last_verified_at`. A record explicitly marked `closed` still
normalizes to `EXPIRED`; `EXPIRED` remains terminal under ADR-007. Existing
`DISCOVERED` jobs become `ACTIVE` when observed again.

Ingestion still performs no per-job GitHub request. Malformed records are still
rejected individually, and a pagination or network failure still rolls back the
job changes of the run, including status and verification updates.

## Alternatives considered

- Keep `DISCOVERED` and implement the authenticated GitHub verifier (#153). It
  confirms each job independently and also detects closed issues, but needs a
  configured token, about one request per job per cycle and new retry/budget
  policy. It remains possible later as additional evidence.
- Unauthenticated per-job verification. Rejected in ADR-003: it exhausts the
  upstream quota and adds a network dependency.
- Match `DISCOVERED` jobs. Rejected: it would weaken the active-only retrieval
  rule for every source instead of recording APiBR-specific evidence.

## Rationale and consequences

The source defines its own listing as open vacancies, and the sample agrees with
that definition, so the listing is explicit source-provided availability
evidence rather than an inference. This makes ingested APiBR jobs eligible for
matching once extraction and embeddings are ready.

The evidence is as fresh as the dataset of the aggregator: its health endpoint
reports the dataset age, and a job closed after the last aggregation can stay
listed until the next one. A job that leaves the listing is not deactivated by
this decision; absence-driven `STALE`/expiry remains #145 and requires a
qualifying snapshot under ADR-013. Source usage and retention rights remain
#134. The sample is a point-in-time observation, not a guarantee of future
source behavior; revisit this decision if the source changes its listing
semantics.
