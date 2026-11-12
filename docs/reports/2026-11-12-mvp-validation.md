# MVP integration validation — 2026-11-12

This is an implementation/evidence record, not release approval. Requirements
remain governed by the feature spec, accepted ADRs and Definition of Done.

## Application and database verification

- Final integrated disposable PostgreSQL/pgvector suite: **531 passed**, one
  opt-in external/model benchmark deselected. Fresh migrations, supported
  downgrade/upgrade paths, concurrent claims/admission/upserts, readiness,
  lifecycle, privacy, source independence and production API ranking are covered.
- Mypy: no issues in 58 source files. Ruff lint and formatting passed.
- Dependency input/provenance validation and seven checker regressions passed.
  All five pip input/hashed-lock pairs are committed. The clean production image
  installed runtime/build dependencies with hashes and passed `pip check`.
- Docker build passed, including actual GLiNER/SentenceTransformers imports as
  non-root UID10001. The image now creates a real passwd/home entry: a bare UID
  previously failed Torch's import-time username/cache resolution.
- Generic Alembic schema check passes. PostgreSQL deparses implicit FTS casts
  differently from SQLAlchemy, so only `ix_jobs_active_fts` is excluded from that
  string comparison. A required separate regression generates a probe index and
  compares server-parsed expression, predicate, method, uniqueness, validity and
  readiness with the migrated index. No other schema differences are suppressed.

## Actual offline measurements

The reference request used the real pinned E5 encoder, PostgreSQL admission,
FTS/vector retrieval, per-entry scoring and REST serialization. With 10,000
ACTIVE jobs, 10 experiences, 5 education entries and limit10, three sequential
warm requests took **2.157, 2.111 and 2.133 seconds**. The five-second target
passed for this homogeneous synthetic corpus with repeated entries and one
CPU inference thread. It is not an arbitrary-request capacity guarantee.
See [machine-readable reference](2026-11-12-cpu-reference.json).

An independent reviewer authored and committed 40 PT/10 EN synthetic cases
before seeing model outputs. Primary review/fixture tests preceded actual local
GLiNER/E5 evaluation. No model downloads were needed for that measurement.

| Semantic per-pair role metric | Combined | Portuguese | English |
| --- | ---: | ---: | ---: |
| Pairwise AUC | 0.989 | 0.994 | 1.000 |
| Accuracy at provisional cutoff | 72% | 72.5% | 70% |

This measures the semantic component, not final blended retrieval quality.
Exact span-plus-class precision/recall was 12.9%/16.5% overall. The configured
extractor deliberately emits unclassified mentions: mandatory recall was zero,
precision undefined, and every mandatory gate failed. Mandatory exclusions
remain disabled. No post-hoc threshold fit or human-reviewed release gold is
claimed. See [aggregate model report](2026-11-12-local-model-evaluation.json) and
[fixture/evaluator provenance](../match/evaluation-fixtures.md).

A one-record optional APiBR probe returned HTTP200 with the expected ID/body/URL
shape, but no availability state. Only keys/counts were retained; no raw source
or poster data was saved. State-free records remain DISCOVERED. This observation
does not establish scan completeness or usage/retention rights. See
[shape report](2026-11-12-source-shape.json).

## Deployment verification

The combined production Compose configuration validates with synthetic
credentials. PostgreSQL has no host port; API exposure is loopback only. Named
database/model volumes, migration ordering, offline serving and model preparation
services are configured. Backup/restore scripts pass mocked safety tests and
ShellCheck. The development database port requires an explicit separate overlay.

The primary's disposable real-model Compose/replacement/restore smoke is recorded
separately; its final observed outcome must be read before claiming deployment
acceptance. Earlier failed attempts are preserved outside the repository. Their
clean-image UID defect was corrected; a transient PostgreSQL recovery response
also exposed the need for bounded readiness retries in the smoke procedure.

## Orchestration and preservation

The primary inspected both checkouts, preserved pre-existing uncommitted work in
a local integration commit and retained original child commits. Three distinct
guest-local branches/worktrees, compiled role/context manifests and transactional
task/attempt reservations preceded native launches. Actual returned UUIDs were
recorded immediately. Children implemented/tested/committed; only the primary
reviewed and integrated. Original custom child reports are preserved alongside
schema-compliant primary completion evidence.

Three old-boot assignments had invalid historical `/root/...` native IDs. The
prior parent was unloaded and its boot no longer existed. A new guarded runtime
command closes only old-boot intervals at confirmed checkpoints, retaining an
unknown active tail; it never bills reboot downtime or invents historical native
UUIDs. Recovered committed work was independently reviewed; the empty interrupted
fixture assignment was cancelled before a distinct replacement was reserved.

Runtime validation: **48 tests**, Ruff lint/format and ShellCheck passed. Runtime
source commit `ed76b67` stays in its standalone local tooling tree; no orphan
runtime branch is pushed into the application repository. Validated backups and
manual resource/health observations were taken. Deterministic maintenance and
watchdog helpers were started during continuation; continuous earlier cadence
is not retrospectively claimed. The completed pip-tools HTTP download cache was
removed only after its resolver stopped; models, state, repositories and reports
were preserved.

This remains the explicitly approved Ubuntu host exception. Debian provisioning,
full native profile/depth/four-child behavior and remaining infrastructure fault
acceptance are unverified. Worktree/role boundaries share a UID and are not OS
tenant isolation. Account five-hour allowance counters are not exposed by the
available tools; no exact remaining balance is asserted. Included native models
were inherited, children closed after review, and no paid inference, fallback
API key, Codex upgrade, competing primary or automatic agent restart was used.

## Release limitations

Release remains unapproved pending calibration/sample sufficiency and the
documented extraction quality gate before mandatory exclusions, source usage/
availability/completeness evidence, and any unverified deployment acceptance.
Language/employment hard-filter mappings remain conservative and unresolved.
External HTTPS termination is not demonstrated by loopback smoke testing.
No production deployment or PR merge is authorized or performed.
