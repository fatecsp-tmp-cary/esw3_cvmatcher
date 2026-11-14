# Policy-updated calibration and former-held-out copies

Authority: [ADR-014](../../../architecture/decisions/ADR-014-extraction-context-and-approximate-evidence.md).

Use [gold.json](gold.json) for the policy-updated evaluator and [changes.json](changes.json)
for every case-level edit and source hash. [source-reviewed-gold.json](source-reviewed-gold.json)
preserves the original reviewed input. No source job/candidate text or partition
ID changed. [calibration.json](calibration.json) contains 20 PT/5 EN reusable
calibration cases. [heldout.json](heldout.json) preserves the old 20 PT/5 EN cases
as **regression/development evidence**, not a new independently reviewed set.

The user authorized these policy edits; the assistant applied them explicitly,
without deriving labels from model outputs. Original human reviewer identifiers
remain provenance for the source labels, not an assertion that the updated labels
received a new independent review. Empty candidates are irrelevant and remain in
role AUC/accuracy; jobs without explicit requirements are not relevant by default.
Original rationales and superseded conventions remain in the source copy/change
record rather than being silently attributed to the current policy.

Generate new copies from the archived source without overwriting it:

```sh
python -m scripts.evaluation.update_extraction_policy_labels \
  --source docs/match/human-review/extraction-policy-v2/source-reviewed-gold.json \
  --output-directory /path/to/new-policy-copies
```

See the [measurement and limitations](../../../reports/2026-11-14-extraction-correction/README.md).
No hard exclusion or release approval follows from any numeric regression result.
