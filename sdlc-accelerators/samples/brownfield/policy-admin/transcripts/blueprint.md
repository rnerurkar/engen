# Transcript — `/accelerator.blueprint` (PolicyAdmin-WebForms)

```
You: /accelerator.blueprint

Agent: Blueprint generation started (task bpf-ee40d56e67a1338a). Checking progress...
Agent: Stage ④: substitution — 4 integrations resolved ✓
Agent: Stage ⑤: pattern retrieval for INT-001...
Agent: Stage ⑤: pattern retrieval for INT-002...
Agent: Stage ⑤: pattern retrieval for INT-003 (cross-cloud)...
Agent: Stage ⑤: pattern retrieval for INT-004...
Agent: Stage ⑤: composition validation ✓ (validate_composition — 14 rules checked)
Agent: Stage ⑥: ADR compliance — 4 integrations passed ✓
Agent: Stage ⑦: assembling app-blueprint.md + app-blueprint.json + diagrams...
Agent: Blueprint ready. Wrote app-blueprint.md and app-blueprint.json to your
       workspace, plus 4 Draw.io diagrams (CSA + TSA + component + DR).
```

**Review checks (per developer guide §13):**

- Lifecycle state: **LIVE** ✓
- Confidence per integration: all ≥ 0.85 ✓ (INT-001, INT-002, INT-003, INT-004)
- `requires_review` flags: none ✓
- Phase-0 entries: cross-cloud plumbing present — coordinate with the network team ✓
- ADR compliance records: match EA expectations ✓

> Note: this archetype produces an **app-blueprint** (PRIMARY) + a derived JSON. Governance is handled separately by Governance Guardian via `/accelerator.assess`.

