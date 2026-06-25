# Transcript — `/accelerator.generate` (LoanOrigination-Monolith)

```
You: /accelerator.generate

Agent: Step 0 — governance gate: calling recordTechDebt on Governance Guardian...
Agent:   no showstoppers → 2 findings recorded as tech debt. Proceeding.
Agent: Brownfield-aware generation (steps 1–18)...
Agent:   • BFF services with feature-flag scaffolding (strangler-fig)
Agent:   • dual-publish config (MQ → SQS) with downstream dedupe by event_id
Agent:   • Apigee client with circuit breaker (PrivateLink → PSC)
Agent:   • Terraform via company-terraform skill (reads tf-modules over GitHub MCP)
Agent:   • Harness pipeline with /accelerator.refresh gate before deploy
Agent:   • AWS Config rules generated from ADR compliance records
Agent: Generation complete. Review the PR.
```

**Generated structure (boilerplate — you add business logic):**

```
loan-origination/
├── services/
│   ├── applicant-portal-spa/            # Angular SPA (CloudFront)
│   ├── origination-core/                # Spring Boot service (Fargate)
│   │   ├── src/main/java/...   # controllers, services, clients  # YOUR CODE HERE
│   │   └── feature-flags.yaml  # strangler-fig routing
│   ├── credit-bureau-api/                # Spring Boot service (Fargate)
│   │   ├── src/main/java/...   # controllers, services, clients  # YOUR CODE HERE
│   │   └── feature-flags.yaml  # strangler-fig routing
│   ├── core-banking-host-link/                # Spring Boot service (Fargate)
│   │   ├── src/main/java/...   # controllers, services, clients  # YOUR CODE HERE
│   │   └── feature-flags.yaml  # strangler-fig routing
├── transition/
│   ├── dual-publish.yaml        # MQ → SQS toggle
│   └── phase-0-checklist.md     # cross-cloud / landing-zone plumbing
├── deployment/
│   └── terraform/
│       └── main.tf              # references github.com/company/tf-modules (GENERATED)
├── compliance/
│   └── aws-config-rules.tf      # from ADR compliance records
└── .harness/
    └── pipeline.yaml            # Jenkins(TF) + Harness(deploy), refresh gate
```

