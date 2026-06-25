You: /accelerator.generate

Agent: Checking staleness... app-blueprint.json in sync ✓
Agent: Checking governance gate (recordTechDebt)...
       Governance passed. Tech debt recorded (TD-2026-0223):
       - F-003: skill-version pin (MEDIUM) — tech debt
       Proceeding with code generation...

credit-memo-refiner-agent/
├── app/
│   ├── agent.py                          ← Root LoopAgent (credit_memo_refiner)
│   ├── sub_agents/
│   │   └── memo_refiner.py               ← LlmAgent (draft / refine / self-score)
│   ├── mcp_connections/
│   │   ├── loan_origination.py           ← MCPToolset (read)
│   │   └── memo_store.py                 ← MCPToolset (read/write)
│   ├── tools/
│   │   └── quality_score_fn.py           ← YOUR CODE HERE
│   ├── callbacks/model_armor.py
│   └── skills/{alloydb, memo-drafting, quality-rubric}/
├── deployment/terraform/
│   ├── main.tf                           ← Company TF modules (via GitHub URLs)
│   ├── identity/agent-identities.tf      ← Workload Identity (2 agents)
│   ├── gateway/apigee-routes.tf          ← 2 Apigee routes
│   ├── environments/{dev,staging,prod}.tfvars
│   └── dr/{failover,failback,lifecycle}.tf
├── observability/{dynatrace, otel}/
├── .harness/pipeline.yaml                ← Harness: infra + build + deploy + promote + API Hub register
├── eval/golden-dataset.json              ← 5 seeded (exits-pass3 / max-passes / stalled / data-unavailable / missing-section)
├── pyproject.toml
├── README.md
└── app-blueprint.md

✅ Project generated. Harness CI/CD takes over after merge.
Next: implement quality_score_fn.py (rubric weights), write the memo_refiner system prompt, open PR.
