# SDLC Accelerators — Sample Suite

Worked samples for the **SDLC Accelerators** platform (formerly AgentCatalyst), organized by archetype
under `samples/`. Every sample is built entirely on the SDLC Accelerators mechanism set (Solution
Accelerator MCP Server, `app-blueprint.md`/`.json`, `validate_composition`, Governance Guardian,
Workload Identity, Apigee + API Hub, Jenkins + Harness, Dynatrace + Splunk + OTel). Nothing in this
suite uses another platform's patented mechanisms — the samples share only generic business scenarios.

```
sdlc-accelerators/
└── samples/
    ├── greenfield/     ← agentic apps built from scratch (ADK agents + tools)
    └── brownfield/     ← existing apps: microservices reference + CSA→TSA modernization
```

## Greenfield — agentic archetype (5 apps)
Built from scratch via the Solution Accelerator. Each: `spec.md` → `plan.md` → `app-blueprint.md`
(9 governance sections) → `app-blueprint.json` → `transcripts/{blueprint,assess,generate}.md`.

| App | Domain | Topology |
|---|---|---|
| `loan-underwriting` | Banking | LlmAgent coordinator: Sequential + Parallel + Loop + HITL |
| `order-issue-resolution` | Retail | Single LlmAgent, dynamic tool use |
| `deal-qualification` | CRM | Sequential → Parallel (4 specialists) → synthesizer |
| `policy-underwriting` | Insurance | Sequential → Parallel (4 assessments) → synthesizer |
| `credit-memo` | Banking | LoopAgent → refiner (self-score, exit ≥0.90) |

## Brownfield — two archetypes (7 apps)

**Microservices archetype** (existing IaC + boilerplate; generate app code only):
| App | Domain | Notes |
|---|---|---|
| `greeting-service` | Reference | Angular + Spring Boot Hello World on existing ECS Fargate + Oracle RDS |

**Modernization archetype — CSA→TSA** (term-cleaned). Each: `spec.md` (Application Modernization Spec
with Integration Inventory INT-XXX) → `plan.md` (Modernization Plan, per-integration R-factors +
cutover) → `app-blueprint.md` (12 sections: Part I §1–§7 governance + Part II §8–§12 technical, with
migration phases + coexistence) → `app-blueprint.json` → `transcripts/{blueprint,assess,generate}.md`.

| App | Domain | Kind | Highlights |
|---|---|---|---|
| `claims-portal-mpa` | Insurance | **reference** | vSphere MPA → AWS SPA; strangler-fig + dual-publish + cross-cloud Apigee |
| `policy-admin` | Insurance | build | .NET WebForms → Angular SPA + Spring Boot; cross-cloud rating |
| `loan-origination` | Banking | build | Java monolith → microservices (strangler-fig); retained mainframe |
| `payments-statements` | Banking | build | Mainframe-fronted → Fargate APIs; PCI; cross-cloud fraud scoring |
| `customer-onboarding-kyc` | Banking | build | ESB/BPEL → API-first SPA + BFF; GDPR + AML; cross-cloud sanctions |
| `billing-collections` | Insurance | build | Oracle Forms + PL/SQL → SPA + scheduled jobs; PCI; MQ→SQS |

> **Archetype note:** greenfield blueprints use **9** governance sections; brownfield-modernization
> blueprints use the **12-section** structure (Part I governance §1–§7 + Part II technical §8–§12) per
> the brownfield developer guide. The microservices reference uses a lighter blueprint because its
> infrastructure already exists and only application code is generated.
