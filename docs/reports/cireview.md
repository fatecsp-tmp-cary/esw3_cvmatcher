# Final CI and dependency review

Reviewed the reconciled tree based on `71cd71b` on 2026-11-12 for task
`01a1cdce-d6c0-782e-837c-a4d90adccc9a` (#163).

The five hashed lock pairs agree with pyproject and recorded provenance. Current
pins shared across build, tooling, development and CPU inference locks agree.
The checker previously skipped build constraints and could record a conflicting
transitive pin. It now validates included packages, overlapping constraints and
shared development/CPU-model pins; three negative regressions cover these cases.
No dependency pins, hashes, provenance or package installations changed.

Inspected existing CI: offline lock consistency, Ruff lint/format, explicit mypy,
unit/API, PostgreSQL integration/e2e, fresh upgrade/downgrade/upgrade and schema
check, and production image build jobs remain present. Integration uses the
pinned pgvector digest and does not accept pytest's no-tests exit status.
The setup action installs hashed dependencies and the local editable project
separately without dependency resolution/build isolation. Docker uses the pinned
Python digest, hashed dependencies, offline model settings, non-root inference
import verification and disabled access logs. Ordinary CI does not fetch model
weights or require live-source calls.

Executed offline checks: lock consistency passed; 10 checker unittests passed;
Ruff lint/format passed for `scripts/dependencies`; project mypy passed all 60
source files with a separate temporary cache; `git diff --check` passed.
An initial new test used a package already constrained by build.lock and was
corrected to independently exercise combined-environment conflicts; its final
run passes. Initial Ruff formatting was corrected before the passing rerun.

Database migrations, image builds, registry hash installation, Compose execution,
GitHub-hosted CI and release acceptance were not executed by this child. The
primary owns those integration checks. This is offline consistency and wiring
evidence, not a release approval or Debian acceptance claim.
