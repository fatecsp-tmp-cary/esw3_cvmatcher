# ADR-027: Bidirectional scoring, dual job vectors and seniority hard filter

- **Status:** Accepted
- **Date:** 2026-11-17
- **Authority:** User planning interview on 2026-11-17 (decisions 1-4 below were
  selected explicitly by the user after alternatives were presented).
- **Supersedes:**
  - [ADR-012](ADR-012-issue-completion-and-evaluation-policy.md) (bounded override
    of the disabled-exclusions rule **for severe seniority gaps only**).
  - [ADR-019](ADR-019-title-first-job-evidence-and-displayed-skills.md) (supersedes
    only the statement that job-field precedence adds no candidate-side seniority
    comparison change or hard filter; title-first job precedence and displayed
    skills remain unchanged).
  - [ADR-025](ADR-025-initial-matching-stack.md) (extended from a single job
    embedding vector to dual job vectors).
  - [Scoring policy](../../match/scoring-policy.md) (supersedes the rule omitting
    specialist/coordinator seniority tracks from ordering).
  All other ADR-012 rules, [ADR-016](ADR-016-inactive-jobs-complete-ranked-matches.md)
  eligibility semantics, [ADR-024](ADR-024-all-result-extraction-and-embedding-readiness.md)
  readiness, privacy and the frozen public contract remain in force.
- **Issues:** #214 (dual vectors), #215 (skills), #216 (seniority), #217 (length
  normalization).
- **Implementation status:** Decision 2 is implemented in #214. Decisions 1, 3
  and 4 are implemented by the stacked PRs for #216, #215 and #217. Calibration and
  reviewed held-out evaluation remain pending.

## Context

Observed rankings showed five coupled problems:

1. Jobs with few explicit skills (typical of APiBR, whose skills come from a few
   labels) scored near 100 on the structured skill ratio `matched/skills`, while
   MeuPadrinho jobs with many `requisitos_tecnicos` and optional items were penalized.
2. One window-averaged vector over title, skills, requirements and the whole
   description diluted the role/stack signal of long postings, so they were
   rarely retrieved or scored low for well-suited candidates.
3. Long candidate profiles produced a large OR text query, an unnormalized
   `ts_rank_cd`, whole-CV skill matching and best-3 experience selection, so they
   scored high on loosely related jobs.
4. Seniority was omitted unless a relevant experience title had an explicit
   marker, overqualification scored 100, and specialist/coordinator tracks were
   never compared: junior profiles were recommended senior/lead roles and senior
   profiles were recommended intern/junior roles.
5. Scoring was one-directional (job skills covered by the candidate), with no
   measure of how focused the candidate is on the job.

## Decision

### 1. Symmetric seniority alignment with a severe-gap hard filter (#216)

- One ladder: `INTERN(0) < JUNIOR(1) < MID(2) < SENIOR(3) < SPECIALIST(4) = COORDINATOR(4)`,
  consistent with the ADR-019 restrictive order.
- Job level: `job.seniority_level`, else an explicit title marker.
- Candidate level: the highest explicit title marker among the already selected
  relevant experiences (semantic score at least 50). Without such a marker, a
  conservative tenure fallback: under 12 months of **total** experience (including
  none) is `JUNIOR`; at least 60 months across the **relevant** experiences is
  `SENIOR`; anything else stays unknown. Total tenure is used for the low end so
  entry-level profiles are recognized; relevant tenure is used for the high end so
  career changers are not blocked from junior roles in a new field. Ongoing
  experience is measured to a request reference date (injectable for tests).
- When both levels are known: a gap of two or more levels **removes the job** from
  the response (both directions); a gap of one keeps it with a seniority dimension
  of 40 and a 0.85 multiplier on the final score; an exact match scores 100.
- When either level is unknown, nothing is filtered and the dimension is omitted.
- Filtering happens before ranking inside each status group, so ADR-016 is
  unchanged: `eligibility` still means active versus not active, filtered jobs are
  simply absent, and the inactive group may still fill remaining positions.

### 2. Dual job vectors (#214)

- Keep the full job passage vector (`jobs.embedding`) and add an internal job-core
  vector built from title, seniority, source skills and REQUIRED requirement
  texts only. It is stored in the separate 1:1 `job_embeddings.core_embedding`
  column, so the canonical `Job` keeps exactly its accepted fields and the vector
  never reaches public payloads.
- The worker embeds both passages in one claim and publishes them in one
  transaction; readiness requires both. The core passage policy is part of the
  embedding model version, so existing jobs are re-embedded after deployment.
- Each candidate entry scores `max(core, 0.65*core + 0.35*full)` on cosine before
  calibration: description detail may lift a matching entry but never pulls a
  matching role/stack below its core similarity.

### 3. Bidirectional tiered skill score (#215)

- Job skills are tiered by current extraction classes: REQUIRED 1.0, PREFERRED
  0.4, NICE_TO_HAVE 0.15. Source-supplied skills without an extraction class
  count as REQUIRED; score-only associations without a class count as PREFERRED.
- Job-to-candidate coverage blends weighted coverage with the
  [ADR-021](ADR-021-mandatory-coverage-score-only.md) mandatory ratio
  (`N=1,2 -> N`, `N>=3 -> max(3, ceil(0.7N))`), then Bayesian-smooths it toward a
  neutral 0.5 prior with strength 2.5 weight units, so a job with one or two
  skills stays near neutral instead of reaching 100.
- Candidate-to-job precision is matched job skills over the candidate's core
  skills (competencies, projects and the three most recent experiences), with the
  denominator capped at 15 so broad but legitimate toolkits are not crushed.
- The skills dimension is `100 * F_beta(coverage, precision)` with beta 1.5
  (coverage weighted 2.25 times precision). This remains score-only.

### 4. Length normalization and profile alignment (#217)

- `ts_rank_cd` uses PostgreSQL document-length normalization (flag 1) and the
  textual score is divided by `1 + 0.15*ln(1 + distinct query terms)` before the
  existing `100*r/(1+r)` bound.
- The candidate text query is a focused, deduplicated projection: experience
  titles, competencies, project titles/technologies, education courses, language
  names and the three most recent experience descriptions. The skill matcher uses
  the same core sections. This is a derived matching representation; the
  normalized candidate still preserves every section (ADR-006).
- A concise candidate summary vector is compared with the job-core vector. It adds
  one core-vector retrieval scan and contributes 25% of the semantic component.
- Profiles with more than three experiences receive a gentle coherence factor
  `0.8 + 0.2*min(1, relevant/ceil(n/2))`, so a long profile cannot cherry-pick
  three loosely related entries.

## Alternatives considered

- **Score-only seniority penalty** (keep ADR-012 fully): offered and recommended;
  the user selected a hard filter for severe gaps.
- **Single pooled vector** (no schema change): about three quarters of the
  expected gain; the user selected dual vectors for accuracy.
- **Second vector column on `jobs`**: rejected because the invariants fix the
  canonical `Job` fields; `job_embeddings` already holds embedding provenance 1:1.
- **Plain Jaccard/F1 over all skills**: does not distinguish requirement tiers and
  still penalizes long optional lists.
- **Hard caps on CV text**: would reject or truncate valid public input (ADR-006).

## Consequences

- Algorithm, requirements, textual, semantic and embedding versions change.
- **Rollout availability gap & deploy order (#214):** Because `ready_predicate`
  requires both `jobs.embedding` and `job_embeddings.core_embedding` (and
  `CORE_TEXT_VERSION` changes `EmbeddingConfig.model_version`), existing
  persisted jobs are withheld from `POST /matches` after deploying the schema
  migration and new code until `EmbeddingWorker` re-embeds them (now 2 passages
  per job: full + core, doubling per-job embedding work). To avoid a zero-result
  window in production, apply `alembic upgrade head`, run/drain `prepare-embeddings`
  (or background `EmbeddingWorker`) against the migrated database, and only then
  cut API traffic over to the new release.
- A severe seniority mismatch can now hide a job. Misestimated seniority is the
  main risk; the tenure fallback is deliberately conservative and unknown never
  filters. Reviewed evaluation must cover both filter directions.
- Coefficients (0.65 core share, tier weights, smoothing strength, beta, cap,
  breadth factor, gap penalty) are provisional development settings, not
  calibrated thresholds. ADR-012 held-out evaluation remains required.
- One additional exact cosine scan runs per request; the 5-second warm CPU target
  must be re-measured.
