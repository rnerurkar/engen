You: /accelerator.generate

Agent: Checking staleness... app-blueprint.json is in sync with app-blueprint.md ✓
Agent: Checking governance gate (recordTechDebt)...
       Governance passed. Tech debt recorded (TD-2026-0207):
       - F-003: model-radar fallback (MEDIUM) — tech debt
       Proceeding with code generation...

Agent: Reading app-blueprint.json + installed skills. Generating project...

loan-underwriting-agent/
├── app/
│   ├── agent.py                          ← Root LlmAgent (loan_coordinator)
│   ├── sub_agents/
│   │   ├── fasttrack_intake.py           ← SequentialAgent
│   │   ├── assessment_fanout.py          ← ParallelAgent
│   │   ├── risk_convergence.py           ← LoopAgent (exit delta<0.02 OR 5 passes)
│   │   └── underwriter_review.py         ← HITL
│   ├── mcp_connections/
│   │   ├── core_banking.py               ← MCPToolset
│   │   ├── credit_bureau.py              ← MCPToolset
│   │   └── collateral_valuation.py       ← MCPToolset
│   ├── a2a_clients/
│   │   └── kyc_aml.py                     ← AgentTool
│   ├── tools/
│   │   ├── tier_router.py                ← YOUR CODE HERE
│   │   └── decision_fn.py                ← YOUR CODE HERE
│   ├── callbacks/
│   │   └── model_armor.py                ← Standard input/output screening
│   └── skills/{alloydb, credit-scoring}/
├── deployment/terraform/
│   ├── main.tf                           ← Company TF modules (via GitHub URLs)
│   ├── identity/agent-identities.tf      ← Per-agent Workload Identity (least-privilege)
│   ├── gateway/apigee-routes.tf          ← One Apigee route per tool binding
│   ├── environments/{dev,staging,prod}.tfvars
│   └── dr/{failover,failback,lifecycle}.tf
├── observability/{dynatrace, otel}/
├── .harness/pipeline.yaml                ← Harness: infra + build + deploy + promote + API Hub register
├── eval/golden-dataset.json              ← 5 seeded (small / mid / large / kyc-hit / risk-unstable)
├── pyproject.toml
├── README.md
└── app-blueprint.md

✅ Project generated. Harness CI/CD takes over after merge (no direct deploy).
Next: implement tier_router.py + decision_fn.py, write agent system prompts, open PR.
