# ADR-003: APiBR availability evidence and partial ingestion

- **Status:** Accepted
- **Date:** 2026-11-07

## Context

APiBR records may lack availability evidence or contain malformed data.
Per-record availability requests add a network dependency, and one malformed
record should not prevent ingestion of valid independent records.
Snapshot completeness remains unproven under ADR-002.

## Decision

- Explicit `open` and `closed` evidence maps to `ACTIVE` and `EXPIRED` within
  the allowed lifecycle transitions. Missing evidence leaves a new job
  `DISCOVERED`; it does not downgrade an existing job or advance verification.
- GitHub availability verification is off by default. Do not perform a hidden
  per-job request. An authenticated, bounded verifier requires separate work.
- Reject malformed records individually, commit valid records, and mark the
  run `PARTIAL` with a rejected-record count and sanitized error information.
- A pagination/network failure still rolls back the run's job changes and
  records `FAILED`. Partial and unproven scans cannot drive absence-based
  lifecycle transitions; `snapshot_complete` remains false.

## Alternatives considered

Unauthenticated per-record verification exhausts the upstream quota and adds a
network dependency to normalization. Implementing an authenticated verifier now
would add configuration and retry policy to the initial slice. Rolling back on
every malformed job prevents ingestion of valid independent records.

## Rationale and consequences

This preserves evidence-based lifecycle behavior and makes partial ingestion
observable without sacrificing valid records. APiBR jobs lacking availability
evidence remain outside active retrieval until verification is implemented.
The worker and source interface remain follow-up work; this decision neither
proves snapshot completeness nor authorizes absence-based expiration.
