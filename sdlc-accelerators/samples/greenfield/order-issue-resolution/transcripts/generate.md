You: /accelerator.generate

Agent: Checking staleness... app-blueprint.json in sync ✓
Agent: Checking governance gate (recordTechDebt)...
       Governance passed. Tech debt recorded (TD-2026-0211):
       - F-003: skill-version pin (MEDIUM) — tech debt
       Proceeding with code generation...

order-issue-resolution-agent/
├── app/
│   ├── agent.py                          ← Root LlmAgent (order_resolution_agent)
│   ├── mcp_connections/
│   │   ├── order_mgmt.py                 ← MCPToolset
│   │   ├── inventory.py                  ← MCPToolset
│   │   ├── payments.py                   ← MCPToolset
│   │   ├── carrier_tracking.py           ← MCPToolset
│   │   └── escalation.py                 ← MCPToolset
│   ├── a2a_clients/
│   │   └── reverse_logistics.py          ← AgentTool
│   ├── tools/
│   │   └── goodwill_credit.py            ← YOUR CODE HERE
│   ├── callbacks/
│   │   └── model_armor.py                ← Standard screening (PAN masking)
│   └── skills/{alloydb, refund-policy}/
├── deployment/terraform/
│   ├── main.tf                           ← Company TF modules (via GitHub URLs)
│   ├── identity/agent-identities.tf      ← Workload Identity (1 agent, 7 tool scopes)
│   ├── gateway/apigee-routes.tf          ← 6 Apigee routes (5 MCP + 1 A2A)
│   ├── environments/{dev,staging,prod}.tfvars
│   └── dr/{failover,failback,lifecycle}.tf
├── observability/{dynatrace, otel}/
├── .harness/pipeline.yaml                ← Harness: infra + build + deploy + promote + API Hub register
├── eval/golden-dataset.json              ← 5 seeded (where-is-order / stuck / refund / goodwill / escalate)
├── pyproject.toml
├── README.md
└── app-blueprint.md

✅ Project generated. Harness CI/CD takes over after merge.
Next: implement goodwill_credit.py, write the agent system prompt (tool-selection guidance), open PR.
