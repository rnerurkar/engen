# Transcript — `/accelerator.assess` (ClaimsPortal-MPA)

```
You: /accelerator.assess

Agent: Packaging governance sections §1–§7 from app-blueprint.md...
Agent: Evaluating architecture compliance...
Agent: Checking pattern adherence...
Agent: Scoring HA/DR readiness...
Agent: Assessment complete.
```

## Governance Guardian scorecard — first pass

| Category | Score |
|---|---|
| Executive clarity | 76/100 |
| Tech stack fit | 78/100 |
| ADR adherence | 77/100 |
| NFR coverage | 75/100 |
| Patterns & topology | 78/100 |
| Component architecture | 77/100 |
| HA/DR readiness | 66/100 |
| **Overall** | **75/100 — Grade C** |

**SHOWSTOPPER (HA/DR):** ADR-205 requires a documented DR strategy with RTO/RPO; blueprint §7 was missing the failover runbook reference. `/accelerator.generate` is **BLOCKED**.

**Fix applied:** Add the Pilot Light failover runbook reference + cross-region backup restore steps to §7; update the ADR-205 record.

```
You: /accelerator.assess   (re-run after fix)

Agent: Assessment complete. No showstoppers.
```

## Governance Guardian scorecard — after fix

| Category | Score |
|---|---|
| Executive clarity | 87/100 |
| Tech stack fit | 87/100 |
| ADR adherence | 87/100 |
| NFR coverage | 87/100 |
| Patterns & topology | 86/100 |
| Component architecture | 86/100 |
| HA/DR readiness | 94/100 |
| **Overall** | **88/100 — Grade B** |

**Remaining findings (non-blocking, recorded as tech debt at generate):**
- _Medium:_ add contract tests for the retained legacy datastore hop.
- _Low:_ document synthetic-canary dashboards in the runbook.

No showstoppers → proceed to `/accelerator.generate`.

