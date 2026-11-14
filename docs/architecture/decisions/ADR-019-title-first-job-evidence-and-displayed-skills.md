# ADR-019: Title-first job fields and trustworthy displayed skills

- **Status:** Accepted
- **Date:** 2026-11-14
- **Authority:** User interview following the extraction correction and branch decision audit.
- **Supersedes:** ADR-017 proposal for job-field precedence, multiple-value resolution and displayed extraction skills; ADR-008 explicit-source precedence for these two fields only. Original ADR-017 is preserved.
- **Implementation status:** Policy recorded; implementation and verification remain pending unless separately evidenced in feature tasks.

## Context

ADR-017 is a proposed draft with labels/body/title precedence and a union of
all associated skills. The user reviewed its concrete alternatives after the
extraction correction introduced score-only approximate/conflicting associations.
The public Job enum fields hold one value each.

## Decision

For seniority_level and work_arrangement independently, use recognized values
in this source order: title, then typed labels, then explicit named body fields.
Recognizable words anywhere in the title may supply a value, not only bracketed
tags; preserve token distinctions such as Remote.com rather than reading Remote
inside a dotted name. For multiple recognized title values choose the most restrictive value;
apply the same order when resolving multiple selected body values. Seniority order: INTERN < JUNIOR < MID < SENIOR < SPECIALIST/COORDINATOR.
SPECIALIST and COORDINATOR have equal precedence; first occurrence in the winning
source breaks their tie. Work-arrangement order: REMOTE < HYBRID < ON_SITE.

Example: title Junior Developer overrides a Senior label. Title Pleno/Sênior maps
to SENIOR; Remoto/Presencial maps to ON_SITE. If the title provides no recognized
value and labels cannot supply a mapped value, a checked explicit body option may
resolve the field. An ambiguous/unmapped label does not block a usable title or
body value. Conflicting labels do not defeat the user-approved checked-body resolution: with
labels Remoto and Presencial, no usable title and a checked body option Remoto,
use REMOTE. A conflicting/ambiguous label source is unusable for precedence;
without a usable body value it remains unknown. An unambiguous label still wins
over a different body value. With a title [Remoto], even an ambiguous label
Remoto/presencial does not block REMOTE from the title.
Body fields remain limited to named fields/checked options, not general prose.

Displayed job.skills is the deterministic normalized union of stored source skills
and exact, affirmative, non-conflicting extracted skills. Exclude approximate,
negated, unknown and conflict-flagged extraction associations from the added display
set even if those associations support score-only matching. Do not infer display
trust from JobSkill rows alone; consult retained extraction provenance. Do not
mutate stored canonical Job.skills or its hash solely to display the union.

Work arrangement remains descriptive and never establishes geographic eligibility.
This job-field precedence does not change candidate-side seniority comparison or
add hard filters; all exclusions remain disabled under the existing decisions.

## Alternatives and rationale

Labels/body/title precedence, title tags only and no title inference were
offered. The user chose title-first words anywhere and strongest mapped values.
For equal-precedence specialist/coordinator values, unknown was offered; the user
selected first occurrence. Displaying every association could present fuzzy or
conflicting support as authoritative; the user selected the exact affirmative
non-conflicting union only.

## Consequences

Supersede ADR-017's proposed precedence/ambiguity and unfiltered display-union
behavior with this accepted policy, preserving its original record. Update #196/
PR #197 implementation/tests for source priority, all ordering/tie cases, ambiguous
labels and checked-body resolution, dotted names and provenance-filtered skills.
Version changed normalization/extraction inputs and reprocessing as required;
preserve API shape/privacy/source identity. Existing draft code still uses
labels/body/title, unique-value rejection and an unfiltered association union;
those behaviors have not been made compliant merely by recording this ADR.
