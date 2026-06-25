You: /accelerator.generate

Agent: Checking staleness... app-blueprint.json in sync ✓
Agent: Checking governance gate (recordTechDebt)...
       Governance passed. Tech debt recorded (TD-2026-0219):
       - F-003: skill-version pin (MEDIUM) — tech debt
       Proceeding with code generation...

policy-underwriting-agent/
├── app/
│   ├── agent.py                          ← Root SequentialAgent (policy_underwriting_flow)
│   ├── sub_agents/
│   │   ├── risk_fanout.py                ← ParallelAgent (4 assessments, non-blocking)
│   │   ├── actuarial_pricing.py / claims_history_check.py / inspection_review.py / reinsurance_check.py
│   │   └── underwriting_synthesizer.py
│   ├── mcp_connections/
│   │   ├── pricing_engine.py / claims_db.py / inspection_store.py / reinsurance_api.py / policy_admin.py
│   ├── a2a_clients/
│   │   └── fraud_signals.py              ← AgentTool
│   ├── tools/
│   │   └── synthesis_fn.py               ← YOUR CODE HERE
│   ├── callbacks/model_armor.py
│   └── skills/{alloydb, actuarial-pricing, fraud-detection}/
├── deployment/terraform/
│   ├── main.tf                           ← Company TF modules (via GitHub URLs)
│   ├── identity/agent-identities.tf      ← Workload Identity (7 agents)
│   ├── gateway/apigee-routes.tf          ← 6 Apigee routes (5 MCP + 1 A2A)
│   ├── environments/{dev,staging,prod}.tfvars
│   └── dr/{failover,failback,lifecycle}.tf
├── observability/{dynatrace, otel}/
├── .harness/pipeline.yaml                ← Harness: infra + build + deploy + promote + API Hub register
├── eval/golden-dataset.json              ← 5 seeded (clean / siu-flag / no-reinsurance / inspection-pending / branch-fail)
├── pyproject.toml
├── README.md
└── app-blueprint.md

✅ Project generated. Harness CI/CD takes over after merge.
Next: implement synthesis_fn.py, write the 5 agent system prompts, confirm non-blocking branch policy, open PR.
