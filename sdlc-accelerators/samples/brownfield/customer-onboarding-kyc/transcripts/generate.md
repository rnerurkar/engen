# Transcript — `/accelerator.generate` (CustomerOnboarding-ESB)

```
You: /accelerator.generate

Agent: Step 0 — governance gate: calling recordTechDebt on Governance Guardian...
Agent:   no showstoppers → 2 findings recorded as tech debt. Proceeding.
Agent: Brownfield-aware generation (steps 1–18)...
Agent:   • BFF services with feature-flag scaffolding (strangler-fig)
Agent:   • Apigee client with circuit breaker (PrivateLink → PSC)
Agent:   • Terraform via company-terraform skill (reads tf-modules over GitHub MCP)
Agent:   • Harness pipeline with /accelerator.refresh gate before deploy
Agent:   • AWS Config rules generated from ADR compliance records
Agent: Generation complete. Review the PR.
```

**Generated structure (boilerplate — you add business logic):**

```
customer-onboarding-kyc/
├── services/
│   ├── onboarding-ui-spa/            # Angular SPA (CloudFront)
│   ├── kyc-orchestration/                # Spring Boot service (Fargate)
│   │   ├── src/main/java/...   # controllers, services, clients  # YOUR CODE HERE
│   │   └── feature-flags.yaml  # strangler-fig routing
│   ├── identity-verification-vendor/                # Spring Boot service (Fargate)
│   │   ├── src/main/java/...   # controllers, services, clients  # YOUR CODE HERE
│   │   └── feature-flags.yaml  # strangler-fig routing
│   ├── sanctions-screening/                # Spring Boot service (Fargate)
│   │   ├── src/main/java/...   # controllers, services, clients  # YOUR CODE HERE
│   │   └── feature-flags.yaml  # strangler-fig routing
├── transition/
│   ├── cutover-flags.yaml
│   └── phase-0-checklist.md     # cross-cloud / landing-zone plumbing
├── deployment/
│   └── terraform/
│       └── main.tf              # references github.com/company/tf-modules (GENERATED)
├── compliance/
│   └── aws-config-rules.tf      # from ADR compliance records
└── .harness/
    └── pipeline.yaml            # Jenkins(TF) + Harness(deploy), refresh gate
```

