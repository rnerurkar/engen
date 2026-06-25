You: /accelerator.generate

Agent: Checking staleness... app-blueprint.json in sync ✓
Agent: Checking governance gate (recordTechDebt)...
       Governance passed. Tech debt recorded (TD-2026-0215):
       - F-003: skill-version pin (MEDIUM) — tech debt
       Proceeding with code generation...

deal-qualification-agent/
├── app/
│   ├── agent.py                          ← Root SequentialAgent (deal_qualification_flow)
│   ├── sub_agents/
│   │   ├── qualification_fanout.py       ← ParallelAgent (4 assessments)
│   │   ├── account_researcher.py
│   │   ├── fit_scorer.py
│   │   ├── risk_analyst.py
│   │   ├── champion_mapper.py
│   │   └── consensus_synthesizer.py
│   ├── mcp_connections/
│   │   ├── firmographics.py / intent_data.py / pipeline_db.py / crm_writeback.py
│   ├── a2a_clients/
│   │   └── data_enrichment.py            ← AgentTool
│   ├── tools/
│   │   └── consensus_fn.py               ← YOUR CODE HERE
│   ├── callbacks/model_armor.py
│   └── skills/{alloydb, icp-scoring}/
├── deployment/terraform/
│   ├── main.tf                           ← Company TF modules (via GitHub URLs)
│   ├── identity/agent-identities.tf      ← Workload Identity (7 agents)
│   ├── gateway/apigee-routes.tf          ← 5 Apigee routes (4 MCP + 1 A2A)
│   ├── environments/{dev,staging,prod}.tfvars
│   └── dr/{failover,failback,lifecycle}.tf
├── observability/{dynatrace, otel}/
├── .harness/pipeline.yaml                ← Harness: infra + build + deploy + promote + API Hub register
├── eval/golden-dataset.json              ← 5 seeded (qualify / disqualify / split / partial-firmographics / assessment-fail)
├── pyproject.toml
├── README.md
└── app-blueprint.md

✅ Project generated. Harness CI/CD takes over after merge.
Next: implement consensus_fn.py, write the 6 agent system prompts, open PR.
