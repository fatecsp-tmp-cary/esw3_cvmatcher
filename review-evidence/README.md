# Isolated reviewed evaluation run

This branch runs the frozen 40 PT/10 EN human-reviewed synthetic corpus under
accepted ADR-012. Only calibration labels select a similarity zero anchor;
the extraction model/settings and cutoff 50 remain unchanged. Configuration is
written and hashed before held-out inference. No deployment or hard exclusions
are enabled. Measurements do not grant human release approval.

Source application revision: 1139ada96caf4ede262c3a26e7c2e7cb4af97478.
The user explicitly adjudicated all remaining uncertainty notes as final decisions.
The reviewed gold preserves those notes as rationale; original local packets remain unchanged.
