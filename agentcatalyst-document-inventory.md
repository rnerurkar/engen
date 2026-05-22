# AgentCatalyst — Complete Document Inventory

## Document Relationship Map

```
                        ┌──────────────────────────────────────┐
                        │         SHARED DOCUMENTS             │
                        │  (common to greenfield + brownfield) │
                        ├──────────────────────────────────────┤
                        │  Operations Runbook                  │
                        │  Governance Guardian Extension       │
                        │  app-blueprint.md Template + Example │
                        └────────────┬─────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
         ┌──────────▼──────┐  ┌─────▼──────┐  ┌─────▼──────────┐
         │   GREENFIELD    │  │  DIAGRAMS  │  │   BROWNFIELD   │
         │   (3 docs)      │  │  (5 PNGs)  │  │   (3 docs)     │
         ├─────────────────┤  ├────────────┤  ├────────────────┤
         │ Architecture    │  │ SLT        │  │ Architecture   │
         │ Developer Guide │  │ Infographic│  │ Developer Guide│
         │ (no playbook —  │  │ Arch Diag  │  │ Op. Playbook   │
         │  uses shared    │  │ BF Arch    │  │                │
         │  runbook)       │  │ BF BP Adv  │  │                │
         └─────────────────┘  └────────────┘  └────────────────┘
```

---

## Complete Inventory (14 files)

### Shared Documents (3)

| # | Filename | Type | Purpose | Consumed by |
|---|---|---|---|---|
| S-1 | `agentcatalyst-operations-runbook-both-options.md` | Operations Runbook | Platform-level operational procedures shared across all archetypes: Vertex AI Search wire-level APIs (§1), MCP tool wire format (§1a), search quality regression (§2), acceptance telemetry (§3), catalog quality (§4), tool lifecycle (§5), failure modes (§6), composition validator (§7), EvalOps operations (§8), Blueprint Advisor MCP Server operations (§9), OAuth 2.1 / Entra ID authentication troubleshooting (§9), Governance Guardian operations (§10), Governance Guardian wire format (§10a) | Both greenfield and brownfield platform engineering teams |
| S-2 | `governance-guardian-architecture.md` | Architecture Extension | Governance Guardian MCP Server design: 5 MCP tools (`assess_start/status/result`, `recordTechDebt`, `getAssessmentHistory`), async MCP Tasks pattern, solution package schema, assessment response + scorecard format, assess-fix-reassess loop, tech debt registry, prompt files, mermaid sequence diagram, infrastructure (AlloyDB tables, Cloud Tasks queue), security, EA assessment engine SLA | Both greenfield and brownfield — the EA assessment engine evaluates against enterprise standards regardless of archetype |
| S-3 | `app-blueprint-md-template-and-fnol-example.md` | Template + Reference Example | 18-section `app-blueprint.md` template structure, workspace file layout (markdown + PNGs + drawio XMLs), MCP delivery mechanism (`blueprint_result` JSON with base64 diagrams), diagram generation pipeline, section-to-consumer mapping, Governance Guardian extraction table, full FNOL reference example (~350 lines), transformation rules | Both greenfield and brownfield — the 18-section template is archetype-agnostic; brownfield blueprints use the same sections with brownfield-specific content (e.g., `migration_phases[]`, `Strangler-Fig` patterns, AWS Terraform modules) |

### Greenfield Documents (3)

| # | Filename | Type | Purpose | Relationship to brownfield |
|---|---|---|---|---|
| G-1 | `agentcatalyst-architecture-archetype-agnostic.md` | Architecture | Core platform architecture for greenfield (GCP-native) application development: 5-layer architecture (Experience → Advisory → Generation → Delivery → Runtime), Blueprint Advisor internals (5 MCP tools, async pipeline, AlloyDB Task Store), OAuth 2.1 + Entra ID mermaid sequence diagram, IaC generation via GitHub MCP Server (5-step flow with pattern repos + service modules), `app-blueprint.md` template section (18 sections), Governance Guardian integration (end-to-end thread, governance gate, cost), production readiness checklist, risks, cost model (TCO/ROI) | Brownfield architecture (B-1) references this for: Layer 2 Security (OAuth 2.1), Layer 3 IaC generation flow, app-blueprint.md template, EvalOps design. Greenfield covers GCP-native patterns (ADK agents, Cloud Run, Agent Engine); brownfield covers AWS migration patterns (Spring Boot, ECS Fargate, Aurora) |
| G-2 | `agentcatalyst-archetype-agnostic-developer-guide.md` | Developer Guide | Step-by-step greenfield workflow: `/specify` → `/plan` → `/catalyst.blueprint` → review → `/catalyst.assess` → `/catalyst.generate`. OAuth 2.1 first-time auth note. `/catalyst.assess` section (§2.7a). Governance gate in `/catalyst.generate` (§2.8). IaC generation walkthrough (Terraform via GitHub MCP Server). Spec quality self-check. Troubleshooting (including OAuth 401). Two worked examples: agentic (FNOL) and microservices (Angular + Spring Boot on ECS Fargate) | Brownfield dev guide (B-2) has its own worked example (MPA→SPA migration) and brownfield-specific commands (`/speckit.specify`, `/speckit.plan.draft`, `/speckit.plan.review`, `/catalyst.refresh`). Both reference the same spec template structure, blueprint format, and governance flow |
| G-3 | *(uses S-1 shared runbook)* | — | Greenfield does not have a separate operations playbook — the shared runbook (S-1) covers all platform-level operations | Brownfield has its own playbook (B-3) because it has brownfield-specific operational concerns: ADR constraint store curation, tech substitution table governance, cross-cloud pattern health checks, `/catalyst.refresh` pre-commit hooks, runtime compliance (AWS Config) |

### Brownfield Documents (3)

| # | Filename | Type | Purpose | Relationship to greenfield |
|---|---|---|---|---|
| B-1 | `csa-tsa-speckit-architecture.md` | Architecture | CSA→TSA transformation architecture: 10-stage flow (⓪ CSA Agent → ① speckit.specify → ② plan draft+review → ③ catalyst.blueprint → ④–⑦ Blueprint Advisor pipeline → ⑧ review → ⑧a governance assessment → ⑨ governance gate + generate → 🔄 refresh), brownfield Blueprint Advisor (4-tool with `map_current_to_target`), reference case (vSphere MPA → AWS SPA), cross-cloud egress (PrivateLink + PSC), design contract lifecycle, runtime compliance (AWS Config from ADR attestations), constitution versioning, OAuth 2.1 + Entra ID mermaid diagram, IaC via GitHub MCP Server, inline architecture diagrams | References greenfield (G-1) for: Layer 2 Security (OAuth 2.1 flow), Layer 3 IaC generation (5-step GitHub MCP Server flow), app-blueprint.md template, EvalOps. Adds brownfield-specific: `map_current_to_target` tool, tech substitution table, ADR constraint store, design contract lifecycle, `/catalyst.refresh`, runtime compliance |
| B-2 | `csa-tsa-speckit-developerguide.md` | Developer Guide | Brownfield workflow: CSA diagram → `/speckit.specify` → `/speckit.plan.draft` + `/speckit.plan.review` → `/catalyst.blueprint` → review → `/catalyst.assess` → `/catalyst.generate` → `/catalyst.refresh`. OAuth 2.1 auth note. `/catalyst.assess` section (§13a). Governance gate in `/catalyst.generate` (§14). IaC via GitHub MCP Server. Worked example: Insurance MPA → AWS SPA migration (15 integrations) | References greenfield dev guide (G-2) for: spec template, blueprint format, governance flow. Adds brownfield-specific: `/speckit.specify` (CSA diagram parsing), `/speckit.plan.draft` + `plan.review` (2-stage async EA review), `/catalyst.refresh` (design contract lifecycle), migration-phase awareness, brownfield worked example |
| B-3 | `csa-tsa-speckit-operating-playbook.md` | Operations Playbook | Brownfield-specific operations: ADR constraint store curation, tech substitution table governance, peripheral system health checks, preset publishing, acceptance telemetry, TCO model, failure modes, escalation, Governance Guardian operations (§13a — health checks, Cloud Tasks, AlloyDB maintenance, EA SLA), governance cycle (quarterly with EA office), LOB onboarding (5-week sequence) | References shared runbook (S-1) for: MCP wire format (§1a), search quality (§2), Blueprint Advisor MCP Server operations (§9), OAuth troubleshooting (§9), Governance Guardian ops (§10), Governance Guardian wire format (§10a). Adds brownfield-specific: ADR store curation, substitution table governance, runtime compliance ops (AWS Config), `/catalyst.refresh` pre-commit hooks |

### Diagrams (5 PNGs)

| # | Filename | Used in | What it shows |
|---|---|---|---|
| D-1 | `AgentCatalyst-SLT-Interaction-Diagram.png` | Greenfield architecture (G-1), presentations | 5-step + 2a flow: ❶ Capture Requirements → ❷ AI Architecture Advice → ❷a Governance Assessment (orange) → ❸ Deterministic Scaffold + Governance Gate → ❹ Company CI/CD → ❺ Production Runtime. Includes "What the Developer Does" timing box with `/catalyst.assess`. |
| D-2 | `AgentCatalyst-GA-Architecture-Infographic.png` | Greenfield architecture (G-1), presentations | Same 6-step flow as D-1 in a 3-row infographic layout with color-coded step boxes, artifact boxes between steps, Key Insight, and metrics bar |
| D-3 | `AgentCatalyst-Architecture-Diagram-Updated.png` | Greenfield presentations (slides 2+3), standalone reference | Detailed 8-step component diagram: Developer → Blueprint Advisor + Vertex AI Search + GitHub Repos → app-blueprint.yaml → Developer Reviews → **3a Governance Assessment** (orange) → findings → **4 Scaffold + Governance Gate** (recordTechDebt) → GitHub MCP Server → GitHub Repo + PR → Harness CI/CD → Production |
| D-4 | `agentcatalyst-brownfield-architecture.png` | Brownfield architecture (B-1, §5) | End-to-end brownfield flow: CSA Agent → /speckit.specify → spec.md + plan.md → /catalyst.blueprint → Blueprint Advisor (OAuth 2.1 + Entra ID) with 4-stage pipeline + peripheral systems → app-blueprint.md + diagrams → **Governance Guardian** (orange cluster: assess_start/status/result + recordTechDebt) → governance gate → /catalyst.generate + GitHub MCP Server → GitHub Repo + PR → Harness CI/CD → Runtime Compliance (AWS Config) |
| D-5 | `blueprint-advisor-components.png` | Brownfield architecture (B-1, §9.2) | Blueprint Advisor internals: JSON input (OAuth 2.1 authenticated) → blueprint_start → Cloud Tasks → 4-stage pipeline (map_current_to_target → recommend_architecture → adr_compliance_check → assemble_blueprint) with peripheral stores → AlloyDB Task Store → blueprint_status/result → app-blueprint.md + PNGs + drawio + contract |

---

## Cross-Reference Matrix

How each document references the others:

| From ↓ / To → | G-1 Arch | G-2 Dev | S-1 Runbook | S-2 Gov Guardian | S-3 Template | B-1 Arch | B-2 Dev | B-3 Playbook |
|---|---|---|---|---|---|---|---|---|
| **G-1** Greenfield Arch | — | §2 workflow, §5 schema, §9 troubleshooting | §9 MCP ops, §10 Gov ops | §all (assessment flow) | §18 sections, FNOL example | Layer 3 IaC flow (shared) | — | — |
| **G-2** Greenfield Dev | Layer 2 Security, Layer 3 IaC | — | — | §2.7a assess, §2.8 gate | — | — | — | — |
| **S-1** Shared Runbook | Layer 2 (MCP design) | §2.5 async, §5 blueprint, §14 troubleshooting | — | §10 Gov ops | — | — | — | — |
| **S-2** Gov Guardian | Layer 2 async, Layer 2 Security, Layer 3 IaC | §2.7a assess, §2.8 gate | §10 ops, §10a wire format | — | §18 sections, extraction | — | — | — |
| **S-3** Template | Layer 3 IaC, Layer 2 Security, Layer 2 Task Store | — | — | Assessment extraction | — | — | — | — |
| **B-1** Brownfield Arch | Layer 2 Security (OAuth 2.1), Layer 3 IaC flow | — | §9 MCP ops | §all (assessment flow) | §18 sections | — | §13 review, §14 generate | §9 TCO |
| **B-2** Brownfield Dev | — | Greenfield workflows (§2–3), spec signals (§4) | — | §13a assess flow | — | §9 async, §14 skills, §17.2 Security | — | — |
| **B-3** Brownfield Play | — | — | §1 wire format, §1a, §2, §9, §10, §10a | §all (assessment flow) | — | §all (design decisions) | §all (developer workflow) | — |

---

## How to Navigate

| If you need to... | Start here |
|---|---|
| Understand the overall greenfield architecture | G-1 (`agentcatalyst-architecture-archetype-agnostic.md`) |
| Understand the overall brownfield architecture | B-1 (`csa-tsa-speckit-architecture.md`) |
| Build a greenfield agentic application step-by-step | G-2 (`agentcatalyst-archetype-agnostic-developer-guide.md`) |
| Build a brownfield CSA→TSA migration step-by-step | B-2 (`csa-tsa-speckit-developerguide.md`) |
| Understand the governance assessment flow | S-2 (`governance-guardian-architecture.md`) |
| Understand the app-blueprint.md format | S-3 (`app-blueprint-md-template-and-fnol-example.md`) |
| Operate the platform (MCP Servers, search quality, health checks) | S-1 (`agentcatalyst-operations-runbook-both-options.md`) |
| Operate brownfield-specific concerns (ADR store, substitution table, onboarding) | B-3 (`csa-tsa-speckit-operating-playbook.md`) |
| Troubleshoot OAuth 2.1 / Entra ID authentication | S-1 §9 (Authentication troubleshooting) |
| Troubleshoot Governance Guardian assessment issues | S-1 §10 + §10a (Governance Guardian operations + wire format) |
| Understand IaC generation via GitHub MCP Server | G-1 Layer 3 (IaC generation subsection) |
| Review the OAuth 2.1 authentication flow | G-1 Layer 2 Security (mermaid sequence diagram) or B-1 §17.2 (mermaid sequence diagram) |
