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

## Complete Inventory (15 files)

### Preset Template & FNOL Sample Inventory

The greenfield Agentic SpecKit preset (`agentcatalyst-enterprise`) contains 20 template files (in the Architecture Document Appendix) and 14 FNOL-specific samples (in the Developer Guide Appendix).

#### Skill Templates (6 SKILL.md files + 6 FNOL output samples)

| # | Skill | Type | Purpose | FNOL Sample Shows |
|---|---|---|---|---|
| S1 | `adk-agents/SKILL.md` | Domain | ADK agent patterns: LlmAgent, SequentialAgent, ParallelAgent, LoopAgent constructors, agent tree wiring, callback registration | 6 agent classes (fnol_coordinator, extract_details, parallel_enrichment, enrich_policy, enrich_vehicle, enrich_weather, severity_classifier, human_review) |
| S2 | `adk-tools/SKILL.md` | Domain | ADK tool patterns: FunctionTool with type-safe schemas, MCPToolset.from_server, A2AClient, tool-to-agent binding | 3 MCP connections, 1 A2A client (body-shop), 3 FunctionTools (severity_classifier, coverage_calculator, notification_sender) with first-draft business logic |
| S3 | `company-terraform/SKILL.md` | Overlay | Company IaC: NEVER raw resources, ALWAYS company modules, GitHub MCP Server 5-step flow, multi-region + DR, Gateway proxy routes, per-agent Workload Identity, API Hub registration | Terraform reading §8 → pattern scaffold + service modules + gateway/routes.tf + identity/agent-identities.tf + registry/agent-entry.tf |
| S4 | `company-observability/SKILL.md` | Overlay | Dynatrace + OTel: dashboard-as-code, Cloud Trace spans, structured JSON logging to Splunk, health check endpoints, alert rules | Dynatrace dashboard JSON, OTel collector YAML with Cloud Trace + Dynatrace exporters, @trace decorators on each agent |
| S5 | `company-cicd/SKILL.md` | Overlay | Jenkins + Harness: pipeline definitions (NOT deployment), 3-phase EvalOps (Vertex AI Eval + AutoSxS + HITL), pre-commit hooks, golden dataset structure, API Hub registration post-deployment step | Jenkinsfile, Harness pipeline YAML with canary + rollback + API Hub registration, golden dataset with 5 seeded entries |
| S6 | `company-security/SKILL.md` | Overlay | Model Armor callbacks (segmented input/output), VPC-SC, CMEK, Workload Identity, Secret Manager, no hardcoded secrets | model_armor.py with input_screen + output_screen, PII_FIELDS list from screening_config |

#### Command/Prompt Templates (3 files + 3 FNOL interaction samples)

| # | Command | Purpose | FNOL Sample Shows |
|---|---|---|---|
| P1 | `commands/catalyst.blueprint.md` | Send spec+plan to Blueprint Advisor MCP Server (async), write .md + .json + diagrams to workspace | Complete MCP interaction: blueprint_start → poll with progress → blueprint_result → 12 files written (.md + .json + 4 diagram formats × 2 diagrams) |
| P2 | `commands/catalyst.assess.md` | Extract 7 artifacts from app-blueprint.md (NOT .json), send to Governance Guardian (async), display scorecard + findings | Extraction from §4/§10-§14, ephemeral solution_package, showstopper finding (no cross-region DR), score 88/100 |
| P3 | `commands/catalyst.generate.md` | Governance gate (recordTechDebt → stop/resume), auto-regenerate .json from .md, 18-step skill-guided code generation | Gate pass with TD-2026-0142, hash match check, 18-step generation producing 42 files |

#### Input Templates (3 files + 3 FNOL filled samples)

| # | Template | Purpose | FNOL Sample Shows |
|---|---|---|---|
| T1 | `templates/spec-template.md` | 10-section structured requirements: Business Context, Workflow, Regulatory, Data Systems, External Partners, What We Own, Business Rules, Transformation Rules, Error Handling, Acceptance Criteria | "First the customer calls, then in parallel it enriches from three sources..." + IF/THEN severity rules + 5 GIVEN/WHEN/THEN criteria |
| T2 | `templates/plan-template.md` | Technical questions: region, model, CI/CD, DR, auth, observability, EvalOps | us-east1, gemini-2.0-flash, Jenkins+Harness, pilot-cold DR, Dynatrace+Splunk |
| T3 | `templates/tasks-template.md` | Generated (80-95%) vs manual (5-20%) work breakdown | 87% auto-generated (6 agents, 3 MCP, Terraform, CI/CD), 13% manual (prompts, logic review, eval curation) |

#### Memory Files (4 files — reference material, no FNOL-specific samples)

| # | File | Purpose |
|---|---|---|
| M1 | `memory/adk-reference.md` | ADK framework: imports, agent hierarchy, tool binding, Runner setup, key constraints |
| M2 | `memory/company-patterns.md` | Naming conventions (snake_case/PascalCase), code organization (agents/tools/mcp/a2a), error handling, documentation |
| M3 | `memory/approved-tools.md` | Approved MCP servers, A2A agents (from Apigee API Hub), public APIs — with endpoints and auth methods |
| M4 | `memory/infra-standards.md` | Terraform module versions (pinned), Dynatrace templates, CI/CD pipeline paths, Cloud Run scaling parameters |

#### Other Preset Files (3 files)

| # | File | Purpose |
|---|---|---|
| G1 | `preset.yml` | Manifest: archetype, template/command/memory paths, skill names + versions + sources, coding agent compatibility |
| C1 | `constitution.md` | 20 non-negotiable rules: never deploy, always use company modules, always generate Model Armor/eval hooks/OTel/health checks |
| F2 | `schemas/app-blueprint.schema.json` | JSON Schema for app-blueprint.json: defines all fields (metadata, agents[], tools{}, infrastructure{}, business_rules{}, screening_config{}, evalops{}, nfrs[], pipeline_configs{}, blueprint_hash) |

#### Blueprint Files (template in shared doc, FNOL sample in dev guide)

| # | File | Purpose | FNOL Sample Shows |
|---|---|---|---|
| F1 | `app-blueprint.md` template | 18-section structured markdown (in `app-blueprint-md-template-and-fnol-example.md`) | Complete 18 sections with agents, tools, infra, business rules, eval config |
| F2-sample | `app-blueprint.json` (FNOL) | Machine-readable JSON derived from .md (in Developer Guide Appendix) | Full JSON with 8 agents, 5 MCP servers, 1 A2A agent, 5 infra modules, business rules, screening config, golden dataset |

---

### Shared Documents (3)

| # | Filename | Type | Purpose | Consumed by |
|---|---|---|---|---|
| S-1 | `agentcatalyst-operations-runbook-both-options.md` | Operations Runbook | Platform-level operational procedures shared across all archetypes: Vertex AI Search wire-level APIs (§1), MCP tool wire format (§1a), search quality regression (§2), acceptance telemetry (§3), catalog quality (§4), tool lifecycle (§5), failure modes (§6), composition validator (§7), EvalOps operations (§8), Blueprint Advisor MCP Server operations (§9 — including Eraser.io health checks and `app-blueprint.json` failure modes), OAuth 2.1 / Entra ID authentication troubleshooting (§9), Governance Guardian operations (§10), Governance Guardian wire format (§10a), **Apigee Proxy + Per-Agent Workload Identity + API Hub A2A Operations (§11)** | Both greenfield and brownfield platform engineering teams |
| S-2 | `governance-guardian-architecture.md` | Architecture Extension | Governance Guardian MCP Server design: 5 MCP tools (`assess_start/status/result`, `recordTechDebt`, `getAssessmentHistory`), async MCP Tasks pattern, solution package schema, assessment response + scorecard format, assess-fix-reassess loop, tech debt registry, prompt files, mermaid sequence diagram, infrastructure (AlloyDB tables, Cloud Tasks queue), security, EA assessment engine SLA | Both greenfield and brownfield — the EA assessment engine evaluates against enterprise standards regardless of archetype |
| S-3 | `app-blueprint-md-template-and-fnol-example.md` | Template + Reference Example | 18-section `app-blueprint.md` template structure, workspace file layout (markdown + `app-blueprint.json` (derived) + `.eraser` + `.drawio.xml` + `.svg` + PNGs), MCP delivery mechanism (`blueprint_result` JSON with `markdown`, `blueprint_json`, and base64 diagrams in 4 formats), diagram generation pipeline via **Eraser.io API**, 3-tool editing model (Eraser.io / Draw.io / Canva), section-to-consumer mapping, Governance Guardian extraction table (reads `.md` NOT `.json`), **API Hub A2A discovery** in §5 Tool Bindings (`body-shop-a2a` discovered via `Apigee API Hub`), **Apigee proxy + Workload Identity** generation note in §4, **API Hub registration** post-deployment step in §17, full FNOL reference example (~350 lines), transformation rules | Both greenfield and brownfield — the 18-section template is archetype-agnostic; brownfield blueprints use the same sections with brownfield-specific content (e.g., `migration_phases[]`, `Strangler-Fig` patterns, AWS Terraform modules) |

### Greenfield Documents (3)

| # | Filename | Type | Purpose | Relationship to brownfield |
|---|---|---|---|---|
| G-1 | `agentcatalyst-architecture-archetype-agnostic.md` | Architecture | Core platform architecture for greenfield (GCP-native) application development: 5-layer architecture (Experience → Advisory → Generation → Delivery → Runtime), Blueprint Advisor internals (5 MCP tools, async pipeline, AlloyDB Task Store), OAuth 2.1 + Entra ID mermaid sequence diagram, IaC generation via GitHub MCP Server (5-step flow with pattern repos + service modules), `app-blueprint.md` (PRIMARY) + `app-blueprint.json` (DERIVED) template section (18 sections), diagram generation via **Eraser.io API** (3-tool editing: Eraser.io / Draw.io / Canva), Governance Guardian integration (reads `.md` NOT `.json`, end-to-end thread, governance gate, cost), **Apigee API Hub** as unified catalog for A2A agent discovery (`search_a2a_agents()`), **Apigee proxy route generation** (one per tool binding), **per-agent Workload Identity** (least-privilege IAM from topology + tool bindings), **API Hub registration** flywheel (post-deployment CI/CD step), production readiness checklist (18 items), risks, cost model (TCO/ROI) | Brownfield architecture (B-1) references this for: Layer 2 Security (OAuth 2.1), Layer 3 IaC generation flow, app-blueprint.md template, EvalOps design. Greenfield covers GCP-native patterns (ADK agents, Cloud Run, Agent Engine); brownfield covers AWS migration patterns (Spring Boot, ECS Fargate, Aurora) |
| G-2 | `agentcatalyst-archetype-agnostic-developer-guide.md` | Developer Guide | Step-by-step greenfield workflow: `/specify` → `/plan` → `/catalyst.blueprint` → review → `/catalyst.assess` → `/catalyst.generate`. Blueprint delivery: `app-blueprint.md` (PRIMARY) + `app-blueprint.json` (DERIVED) + diagrams (`.eraser` + `.drawio.xml` + `.svg` + `.png`). Diagram editing subsection with 3-tool table (Eraser.io / Draw.io / Canva / Mermaid). OAuth 2.1 first-time auth note. `/catalyst.assess` section (§2.7a — reads `.md` NOT `.json`). Governance gate in `/catalyst.generate` (§2.8 — auto-regenerates `.json` from `.md`). IaC generation walkthrough (Terraform via GitHub MCP Server). Apigee proxy, per-agent Workload Identity, and API Hub registration in auto-generated list. Spec quality self-check. Troubleshooting (including OAuth 401). Two worked examples: agentic (FNOL) and microservices (Angular + Spring Boot on ECS Fargate) | Brownfield dev guide (B-2) has its own worked example (MPA→SPA migration) and brownfield-specific commands (`/speckit.specify`, `/speckit.plan.draft`, `/speckit.plan.review`, `/catalyst.refresh`). Both reference the same spec template structure, blueprint format, and governance flow |
| G-3 | *(uses S-1 shared runbook)* | — | Greenfield does not have a separate operations playbook — the shared runbook (S-1) covers all platform-level operations | Brownfield has its own playbook (B-3) because it has brownfield-specific operational concerns: ADR constraint store curation, tech substitution table governance, cross-cloud pattern health checks, `/catalyst.refresh` pre-commit hooks, runtime compliance (AWS Config) |

### Brownfield Documents (3)

| # | Filename | Type | Purpose | Relationship to greenfield |
|---|---|---|---|---|
| B-1 | `csa-tsa-speckit-architecture.md` | Architecture | CSA→TSA transformation architecture: 10-stage flow (⓪ CSA Agent → ① speckit.specify → ② plan draft+review → ③ catalyst.blueprint → ④–⑦ Blueprint Advisor pipeline → ⑧ review → ⑧a governance assessment → ⑨ governance gate + generate → 🔄 refresh), brownfield Blueprint Advisor (4-tool with `map_current_to_target`), `app-blueprint.md` (PRIMARY) + `app-blueprint.json` (DERIVED) generation by `assemble_blueprint`, diagram rendering via **Eraser.io API** (3-tool editing: `.eraser` / `.drawio.xml` / `.svg`), `/catalyst.assess` reads `.md` NOT `.json`, `/catalyst.generate` auto-regenerates `.json` from `.md` if changed then reads `.json`, reference case (vSphere MPA → AWS SPA), cross-cloud egress (PrivateLink + PSC), design contract lifecycle, runtime compliance (AWS Config from ADR attestations), constitution versioning, OAuth 2.1 + Entra ID mermaid diagram, IaC via GitHub MCP Server, inline architecture diagrams | References greenfield (G-1) for: Layer 2 Security (OAuth 2.1 flow), Layer 3 IaC generation (5-step GitHub MCP Server flow), app-blueprint.md template, EvalOps. Adds brownfield-specific: `map_current_to_target` tool, tech substitution table, ADR constraint store, design contract lifecycle, `/catalyst.refresh`, runtime compliance |
| B-2 | `csa-tsa-speckit-developerguide.md` | Developer Guide | Brownfield workflow: CSA diagram → `/speckit.specify` → `/speckit.plan.draft` + `/speckit.plan.review` → `/catalyst.blueprint` → review → `/catalyst.assess` → `/catalyst.generate` → `/catalyst.refresh`. Blueprint delivery: `app-blueprint.md` (PRIMARY) + `app-blueprint.json` (DERIVED) + `design_contract.json` + diagrams (`.eraser` + `.drawio.xml` + `.svg` + `.png`). Diagram editing table (Eraser.io / Draw.io / Canva / Mermaid) in §13. OAuth 2.1 auth note. `/catalyst.assess` section (§13a — reads `.md` NOT `.json`). Governance gate in `/catalyst.generate` (§14 — auto-regenerates `.json`). IaC via GitHub MCP Server. Worked example: Insurance MPA → AWS SPA migration (15 integrations) | References greenfield dev guide (G-2) for: spec template, blueprint format, governance flow. Adds brownfield-specific: `/speckit.specify` (CSA diagram parsing), `/speckit.plan.draft` + `plan.review` (2-stage async EA review), `/catalyst.refresh` (design contract lifecycle), migration-phase awareness, brownfield worked example |
| B-3 | `csa-tsa-speckit-operating-playbook.md` | Operations Playbook | Brownfield-specific operations: ADR constraint store curation, tech substitution table governance, peripheral system health checks, preset publishing, acceptance telemetry, TCO model, failure modes (including `app-blueprint.json` out-of-sync/corrupted/directly-edited), **Eraser.io API health checks** and fallback (Draw.io when Eraser.io down), escalation, Governance Guardian operations (§13a — health checks, Cloud Tasks, AlloyDB maintenance, EA SLA), governance cycle (quarterly with EA office), LOB onboarding (5-week sequence) | References shared runbook (S-1) for: MCP wire format (§1a), search quality (§2), Blueprint Advisor MCP Server operations (§9), OAuth troubleshooting (§9), Governance Guardian ops (§10), Governance Guardian wire format (§10a), Apigee Proxy + WI + API Hub ops (§11). Adds brownfield-specific: ADR store curation, substitution table governance, runtime compliance ops (AWS Config), `/catalyst.refresh` pre-commit hooks |

### Diagrams (4 PNGs + 1 Mermaid)

| # | Filename | Used in | What it shows |
|---|---|---|---|
| D-1 | `AgentCatalyst-SLT-Interaction-Diagram.png` | Greenfield architecture (G-1), presentations | End-to-end greenfield flow with **Apigee API Hub** (A2A agent discovery), **Eraser.io API** (diagram rendering), `assemble_blueprint` generating `.md` (PRIMARY) + `.json` (DERIVED) + `.eraser` + `.drawio` + `.svg` + `.png`. Code generation producing **Apigee proxy routes + Per-agent Workload Identity + API Hub registration entry**. 7-step + 2a flow with Governance Guardian. |
| D-2 | `AgentCatalyst-GA-Architecture-Infographic.png` | Greenfield architecture (G-1), presentations | How It Works infographic: ❶ Capture Requirements → ❷ AI Architecture Advice (**+ API Hub for A2A agents**) → ❷a Governance Assessment → ❸ Deterministic Scaffold (**+ Apigee proxy + Workload Identity + API Hub registration + Eraser.io diagrams**) → ❹ Company CI/CD → ❺ Production Runtime. Includes "What the Developer Does" timing and Key Insight with A2A flywheel. |
| D-3 | `agentcatalyst-brownfield-architecture.png` | Brownfield architecture (B-1, §5) | End-to-end brownfield flow: CSA Agent → /speckit.specify → spec.md + plan.md → /catalyst.blueprint → Blueprint Advisor (OAuth 2.1 + Entra ID) with 4-stage pipeline (including **Eraser.io API** for diagram rendering) + peripheral systems → **app-blueprint.md (PRIMARY) + app-blueprint.json (DERIVED) + diagrams (.eraser + .drawio + .svg + .png)** → **Governance Guardian** (reads `.md` NOT `.json`, orange cluster: assess_start/status/result + recordTechDebt) → governance gate → /catalyst.generate (**auto-regenerates .json from .md**, reads `.json` for code gen) + GitHub MCP Server → GitHub Repo + PR → Harness CI/CD → Runtime Compliance (AWS Config) |
| D-4 | `blueprint-advisor-components.png` | Brownfield architecture (B-1, §9.2) | Blueprint Advisor internals: JSON input (OAuth 2.1 authenticated) → blueprint_start → Cloud Tasks → 4-stage pipeline (map_current_to_target → recommend_architecture + **search_a2a_agents (API Hub)** → adr_compliance_check → assemble_blueprint via **Eraser.io API**) with peripheral stores → AlloyDB Task Store → blueprint_status/result → **app-blueprint.md (PRIMARY) + app-blueprint.json (DERIVED) + .eraser + .drawio.xml + .svg + PNGs + contract** |
| D-5 | `blueprint-advisor-sequence.mmd` | Greenfield architecture (G-1, §9.3) | Blueprint Advisor async sequence (mermaid): 3-phase flow (Start → Poll → Retrieve) with **Eraser.io API** participant for diagram rendering, **search_a2a_agents** step querying API Hub for deployed A2A agents, `assemble_blueprint` generating `app-blueprint.md` (18 sections) + `app-blueprint.json` (derived) + diagrams (.eraser + .drawio + .svg + .png) |

---

## Cross-Reference Matrix

How each document references the others:

| From ↓ / To → | G-1 Arch | G-2 Dev | S-1 Runbook | S-2 Gov Guardian | S-3 Template | B-1 Arch | B-2 Dev | B-3 Playbook |
|---|---|---|---|---|---|---|---|---|
| **G-1** Greenfield Arch | — | §2 workflow, §5 schema, §9 troubleshooting | §9 MCP ops, §10 Gov ops, **§11 Apigee/WI/API Hub ops** | §all (assessment flow) | §18 sections, FNOL example, **Eraser.io, .json delivery** | Layer 3 IaC flow (shared) | — | — |
| **G-2** Greenfield Dev | Layer 2 Security, Layer 3 IaC, **Eraser.io diagram gen, .json flow** | — | **§11 proxy/WI/API Hub ops** | §2.7a assess, §2.8 gate | **§18 sections, FNOL example** | — | — | — |
| **S-1** Shared Runbook | Layer 2 (MCP design) | §2.5 async, §5 blueprint, §14 troubleshooting | — | §10 Gov ops | **§18 template for blueprint format** | — | — | — |
| **S-2** Gov Guardian | Layer 2 async, Layer 2 Security, Layer 3 IaC | §2.7a assess, §2.8 gate | §10 ops, §10a wire format | — | §18 sections, extraction | — | — | — |
| **S-3** Template | Layer 3 IaC, Layer 2 Security, Layer 2 Task Store, **Eraser.io diagram gen, .json delivery, API Hub A2A** | — | — | Assessment extraction | — | — | — | — |
| **B-1** Brownfield Arch | Layer 2 Security (OAuth 2.1), Layer 3 IaC flow, **Eraser.io, .json flow** | — | §9 MCP ops, **§11 proxy/WI/API Hub ops** | §all (assessment flow) | §18 sections, **Eraser.io, .json** | — | §13 review, §14 generate | §9 TCO |
| **B-2** Brownfield Dev | — | Greenfield workflows (§2–3), spec signals (§4) | — | §13a assess flow | — | §9 async, §14 skills, §17.2 Security, **Eraser.io, .json** | — | — |
| **B-3** Brownfield Play | — | — | §1 wire format, §1a, §2, §9, §10, §10a, **§11** | §all (assessment flow) | — | §all (design decisions) | §all (developer workflow) | — |

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
