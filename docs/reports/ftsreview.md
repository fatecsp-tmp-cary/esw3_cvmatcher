# Independent FTS integration review

Reviewed base `71cd71b0935fc2ca5398e14bf830439ecda00b0e` for runtime task
`01a1cdce-d399-775c-99b9-fec0fe54f463` on 2026-11-12. No concrete FTS
implementation defect was found; no application behavior was changed.

The shared expression retains accepted ADR-004/005 Portuguese fields, A/B/D
weights and PostgreSQL JSON text rendering. Query input is bound;
`plainto_tsquery` lexemes are OR-combined and cast directly to `TSQUERY`.
Job and requirement paths both require ACTIVE and the supplied extraction gate;
omitted readiness fails closed. Compiling with the actual extraction predicate
confirmed SUCCEEDED, matching content hash and configuration checks in both
branches. Requirement-only matches survive the union; maximum requirement rank
avoids multiplying duplicate rows. Raw ranks are summed before bounded conversion.
Publication-date-descending/nulls-last and source identity resolve retrieval ties.

The production pipeline supplies current extraction readiness, uses the complete
requirement-aware textual statement when scoring its retrieved union, and
includes the textual policy in its algorithm-version digest. Candidate query
text stays request-scoped. This review found no candidate persistence/logging or
geographic filtering introduced by FTS.

Executed in the assigned isolated worktree:

- `python -m pytest --no-cov -q tests/unit/indexing tests/unit/matching/test_textual_search.py`:
  24 passed, exit 0.
- `ruff check --no-cache src/indexing/textual.py src/matching/textual.py tests/unit/indexing tests/unit/matching/test_textual_search.py tests/integration/indexing tests/integration/test_textual_search.py`:
  passed, exit 0.
- `ruff format --check --no-cache` over those same paths: six files formatted,
  exit 0.
- `python -m mypy --cache-dir /tmp/cvmatcher-ftsreview-mypy src/indexing/textual.py src/matching/textual.py`:
  success, two source files, exit 0.
- `git diff --check`: passed, exit 0.

Commands use the approved tools under `/home/agent/workspace/cvmatcher-dev/bin`.
The existing database regressions cover requirement-only matches, duplicate
requirements, readiness, field weights, publication ties and indexing. They were
inspected but **not executed** in this assignment. The primary owns serialized
PostgreSQL checks, migration/index acceptance, integrated pipeline validation,
Compose/image execution and final measurements. This review does not establish
release calibration, source terms/completeness, production deployment or
performance after reconciliation. No DB/Docker, secret access, package changes,
remote operations or delegation were performed.
