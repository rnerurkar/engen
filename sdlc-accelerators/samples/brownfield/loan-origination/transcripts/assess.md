# Transcript — `/accelerator.assess` (LoanOrigination-Monolith)

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
| Executive clarity | 79/100 |
| Tech stack fit | 81/100 |
| ADR adherence | 80/100 |
| NFR coverage | 78/100 |
| Patterns & topology | 81/100 |
| Component architecture | 80/100 |
| HA/DR readiness | 69/100 |
| **Overall** | **78/100 — Grade C** |

**SHOWSTOPPER (HA/DR):** ADR-205 requires cross-region DR for Tier 1; blueprint §7 shows single-region only. `/accelerator.generate` is **BLOCKED**.

**Fix applied:** Add Warm Standby in the DR region (cross-region RDS read-replica + pre-provisioned Fargate services + Route 53 failover) and update §7 + ADR-205 record.

```
You: /accelerator.assess   (re-run after fix)

Agent: Assessment complete. No showstoppers.
```

## Governance Guardian scorecard — after fix

| Category | Score |
|---|---|
| Executive clarity | 90/100 |
| Tech stack fit | 90/100 |
| ADR adherence | 90/100 |
| NFR coverage | 90/100 |
| Patterns & topology | 89/100 |
| Component architecture | 89/100 |
| HA/DR readiness | 97/100 |
| **Overall** | **91/100 — Grade A** |

**Remaining findings (non-blocking, recorded as tech debt at generate):**
- _Medium:_ add contract tests for the retained legacy datastore hop.
- _Low:_ document synthetic-canary dashboards in the runbook.

No showstoppers → proceed to `/accelerator.generate`.

