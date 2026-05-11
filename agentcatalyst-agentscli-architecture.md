# AgentCatalyst — agents-cli GA-Only Architecture

**A spec-driven enterprise agent development accelerator on Google Cloud Platform**
*Uses agents-cli for scaffolding · GA-only runtime services · agents-cli eval/simulate/deploy FORBIDDEN*

> **Note:** This document contains Mermaid.js diagrams in fenced code blocks. To render them as images, use a Mermaid-compatible viewer (VS Code with Mermaid Preview extension, GitHub, or mermaid.live). Standard markdown viewers will display the diagram source code instead.

---

## Executive Summary — For the SLT

### The problem

Every enterprise team building AI agents today follows its own approach. Copilot helps write code faster, but it has no knowledge of company patterns, no understanding of compliance standards, and no ability to recommend architectures from organizational catalogs. The result: 50 teams produce 50 different implementations, 82 hours of compliance rework per use case, and 30+ POCs that never reach production.

### The solution: AgentCatalyst (agents-cli variant)

AgentCatalyst is a spec-driven agent development accelerator with three core capabilities:

1. **Blueprint Advisor** — an LlmAgent exposed as an MCP Server that recommends architectures by searching company-curated catalogs via RAG. The developer's coding agent connects via MCP protocol, calls `recommend_architecture(spec, plan)`, and receives a YAML blueprint describing WHAT to build. The developer reviews and edits the YAML — the human is always in control.

2. **agents-cli scaffolding with GA-only deployment** — project scaffolding uses `agents-cli scaffold create` (which bundles Google's 7 skills automatically), but deployment uses exclusively GA runtime services (Cloud Run, Apigee, Workload Identity). The commands `agents-cli eval`, `agents-cli simulate`, and `agents-cli deploy` are **FORBIDDEN** — a three-layer skill override enforces this. All evaluation goes through Arize + Jenkins/Harness, not Google's preview tooling.

3. **Skill-constrained code generation** — the coding agent (Copilot, Claude Code, Cursor) is constrained by three layers: the blueprint (WHAT), the archetype skill (HOW), and the overlay skills (MUST). Constitution.md encodes non-negotiable code generation rules. The coding agent generates a first draft of the complete application — including working business logic from structured rules in the spec — for the developer to review and make their own.

AgentCatalyst does NOT deploy agents. It generates code, infrastructure definitions, and CI/CD pipeline files — then commits everything to the developer's GitHub repo. The company's existing Jenkins + Harness pipelines take it to production.

### Why agents-cli scaffolding with GA-only runtime?

| Benefit | How |
|---|---|
| **7 bundled skills for free** | `agents-cli scaffold create` bundles Google's BigQuery, Cloud SQL, Cloud Run, Firebase, GKE, Gemini API, and Security/Reliability/Cost skills — no manual installation |
| **Familiar project structure** | Google's recommended ADK project layout out of the box |
| **SLA-backed runtime** | Cloud Run + Apigee + Workload Identity — all GA, all with SLAs |
| **CI/CD governance** | `eval/simulate/deploy` FORBIDDEN prevents developers from bypassing Jenkins/Harness |
| **No preview risk** | Runtime is GA-only. agents-cli is used only for scaffolding (one-time action) |

### Key principles

1. **Spec-driven, not prompt-driven.** Structured 10-section templates with business rules — not free-form chat prompts.
2. **AI-advised, human-decided.** The Blueprint Advisor recommends; the developer reviews and edits the YAML. The human is always in control.
3. **Compliant by construction.** Company overlay skills teach the coding agent non-negotiable standards. Compliance is structural, not retrofitted.
4. **Scaffolding convenience, deployment governance.** `agents-cli scaffold create` for the easy start; Jenkins/Harness for the governed deploy. Never `agents-cli deploy`.
5. **Generates, never deploys.** Code and pipeline definitions committed to GitHub. The company's CI/CD deploys.

**Supported coding agents:** Officially tested: **Copilot, Claude Code, Cursor**. Compatible (community-tested): Gemini CLI, Windsurf. Any Spec Kit-compatible coding agent should work — the preset and skills follow the agentskills.io standard.

### The ROI

| Metric | Value | Derivation |
|---|---|---|
| Per use case savings | **$39K (74%)** | $52.8K without → $13.8K with AgentCatalyst |
| Platform investment (Year 1) | **$51K** | Build $25K (250 hrs × $100) + GCP infra $12K ($1K/mo) + maintenance $14K (35 hrs/quarter) |
| Break-even | **2nd use case** | 2 × $39K savings = $78K > $51K platform cost |
| Enterprise investment (7 LOBs) | **$170K** | Platform $51K + LOB onboarding 7 × $17K ($119K) |
| Enterprise savings (210 use cases) | **$8.19M** | 210 × $39K per use case |
| Enterprise ROI | **48×** | $8.19M savings / $170K total investment |
| Each additional LOB | **$17K** to onboard |
| Time to first agent | **~3.5 weeks** (down from ~7.5 weeks) |

### Per use case cost comparison (both sides use Copilot)

| | Without AgentCatalyst (Copilot + published standards) | With AgentCatalyst (Copilot + skills + Blueprint Advisor) |
|---|---|---|
| **Build phase** | 446 hrs (requirements 60 + standards learning 24 + architecture 60 + code 100 + prompts 35 + infra/CI/CD/obs/security 82 + testing 60 + deploy 25) | 138 hrs (requirements 60 + spec/plan/biz rules 8 + Blueprint Advisor 1 + generate 1 + complex domain logic 20 + prompts 25 + testing 15 + PR 8) |
| **Compliance remediation** | 82 hrs (EA review 16 + security review 16 + rework 50) | 0 hrs (compliant by construction — overlay skills enforce company standards; constitution.md constrains code generation) |
| **Total** | **528 hrs / $52.8K / ~7.5 weeks** | **138 hrs / $13.8K / ~3.5 weeks** |
| **Savings** | | **$39K per use case (74%)** |

† If business rules are NOT captured in the spec, add $5.5K per use case (55 hrs) for manual business logic implementation → $19.3K / 193 hrs per use case. Enterprise savings drop from $8.0M to $6.85M but ROI remains 36×.

Note: Requirements gathering (60 hrs) is identical on both sides. AgentCatalyst does not reduce the time to gather requirements — it reduces the time to go from requirements to production-ready code.

### GA-only commitment

Every GCP runtime service used by AgentCatalyst is Generally Available with SLA backing. `agents-cli` is used only for one-time scaffolding — all runtime services are GA. No preview APIs. No preview services. Deployable in any GCP project, including locked-down enterprise environments.

---

## End-to-end thread (read this first)

A developer is asked to build an AI agent that processes auto insurance claims (FNOL). She opens VSCode with her preferred coding agent — Claude Code — and runs `agents-cli scaffold create fnol-agent --template adk_a2a`. This creates a complete project structure with Google's 7 bundled skills pre-installed — BigQuery, Cloud SQL, Cloud Run, Firebase, GKE, Gemini API, and Security/Reliability/Cost pillars. No manual skill installation needed.

She installs the AgentCatalyst preset: `specify preset add agentcatalyst-enterprise`. This adds the structured spec template, plan template, custom commands, memory files, company overlay skills, and the `adk-agents` domain skill on top of the scaffolded project.

She types `/specify`. The preset presents a structured template with ten sections — Business Context, Workflow Step by Step, Regulatory Requirements, Data Systems, External Partners, What We Own, Business Rules, Transformation Rules, Error Handling, and Acceptance Criteria. She fills it in with ordering words, data systems, partner APIs, and structured IF/THEN business rules. This takes about 20 minutes. The result is `spec.md`.

She types `/plan` and answers technical questions — GCP region, LLM model, CI/CD tools, Terraform module source. The result is `plan.md`.

She types `/catalyst.blueprint`. This custom command connects to the **Blueprint Advisor MCP Server** — an LlmAgent running on Cloud Run, exposed as an MCP Server. Her coding agent calls the `recommend_architecture` tool via MCP protocol. The Blueprint Advisor searches the company's catalogs via RAG, applies LLM reasoning guided by a company system prompt, and returns recommendations with confidence scores. Her coding agent saves them as `app-blueprint.yaml` — 5 agents, 3 MCP servers, 3 A2A agents, 3 FunctionTool implementations with her business rules, infrastructure settings, EvalOps config, and a golden dataset.

She reviews the YAML and edits one field. Her coding agent calls `validate_composition` via MCP (deterministic adjacency check), then `assemble_blueprint` (deterministic YAML finalization).

She types `/catalyst.generate`. The coding agent reads the YAML and generates all the code, constrained by: the blueprint (WHAT), the `adk-agents` archetype skill (HOW), the company overlay skills (MUST), and `constitution.md` (non-negotiable coding rules — NOT meta-skills).

**Critically, the company-cicd overlay skill contains an explicit override:** "Generate Jenkins + Harness pipeline definitions. NEVER deploy directly via `agents-cli deploy`." This is enforced at three layers:
1. The company-cicd skill instruction (tells the coding agent what to generate)
2. The constitution.md rule (absolute: "NEVER run agents-cli deploy")
3. A `.agentcli-overrides.yaml` file in the project root that disables the deploy command at the CLI level

The result: a complete project — 6 agent class files, 3 MCP connections, 3 A2A clients, 3 FunctionTool files with first-draft business logic (IF/THEN conditions from her spec already implemented as working Python code), Model Armor callbacks, Terraform, Dynatrace config, Jenkins + Harness pipelines, pre-commit hook, Phoenix tracing, golden dataset, and 3-phase Harness evaluation pipeline.

She opens `app/tools/severity_classifier.py` and reviews the first draft — this is her starting point, not a black box. She refines the logic, adds one edge case, writes system prompts. The manual work is ~5–10%.

She might want to run `agents-cli eval` for a quick local test — but she can't. The three-layer override blocks it. Instead, she commits. The pre-commit hook runs — 5 evalsets in under 60 seconds. All pass.

After PR merge, Jenkins runs Terraform, then Harness deploys through 3-phase EvalOps (Arize gates → AutoSxS → HITL triage) and promotes Non-Prod → Pre-Prod (canary) → Production.

She never deployed from her laptop. She never ran `agents-cli deploy`. Every runtime service is GA with SLA backing.

**Total time from "I need an FNOL agent" to generated code committed to GitHub: under 2 hours.** Without AgentCatalyst: 7–8 weeks.

---

## Technology Stack

| Component | Details |
|---|---|
| Agent Framework | Google ADK — Python |
| Scaffolding | `agents-cli scaffold create` (7 Google skills bundled) |
| Runtime | Cloud Run (GA) — NOT Agent Engine |
| Gateway | Apigee Runtime Gateway (GA) — NOT Agent Gateway |
| Identity | Workload Identity (GA) — NOT Agent Identity |
| Blueprint Advisor | LlmAgent exposed as **MCP Server** on Cloud Run |
| Discovery | Vertex AI Search (pattern catalog, skill catalog, tool registry) |
| IaC | Terraform + company TF modules via GitHub MCP Server |
| Security | Model Armor (standard — segmented is future roadmap), DLP, Secret Manager, SPIFFE, VPC-SC, CMEK |
| Observability | OTel → Dynatrace (APM) + Splunk (SIEM) + Arize Phoenix (traces) |
| Evaluation | Arize SaaS + Vertex AI Eval SDK + AutoSxS + HITL triage |
| CI/CD | Jenkins (infra) + Harness (deploy + 3-phase EvalOps) |
| MCP Protocol | Version **2025-03-26** (tested with Copilot, Claude Code, Cursor) |
| **FORBIDDEN** | **`agents-cli eval`, `agents-cli simulate`, `agents-cli deploy`** |

---

## Five-Layer Architecture

```
Layer 1 — SPEC CAPTURE         agents-cli scaffold → /specify → spec.md, /plan → plan.md
Layer 2 — ARCHITECTURE ADVISORY Blueprint Advisor MCP Server → app-blueprint.yaml
Layer 3 — SKILL-GUIDED GEN     /catalyst.generate → complete project (deploy FORBIDDEN)
Layer 4 — COMPANY CI/CD        Jenkins (infra) + Harness (deploy + EvalOps)
Layer 5 — RUNTIME & OPERATE    Cloud Run + Apigee + Dynatrace + Splunk
```

### Layer 1 — Spec Capture

> For step-by-step walkthroughs, see Developer Guide, Section 2.

The developer scaffolds with `agents-cli scaffold create` (gets 7 bundled skills), then installs the AgentCatalyst preset. The preset adds the 10-section spec template (including 4 business logic sections), plan template, custom commands, memory files, and skills.

| Section | Purpose | Impact on code generation |
|---|---|---|
| Business Problem | Context and value proposition | Informs Blueprint Advisor |
| Workflow | Step-by-step with ordering words | Maps to patterns |
| Data Sources | Data systems with workload types | Maps to MCP connections |
| External Integrations | Partner services | Maps to A2A or FunctionTool wrappers |
| Internal Capabilities | Proprietary logic | Maps to FunctionTool implementations |
| Infrastructure | GCP region, compliance, networking | Maps to Terraform |
| **Business Rules** | Structured IF/THEN per decision point | Generates first-draft business logic |
| **Transformation Rules** | Field mappings and formulas | Generates transformation functions |
| **Error Handling** | Timeout/retry per dependency | Generates try/catch with circuit breakers |
| **Acceptance Criteria** | GIVEN/WHEN/THEN assertions | Generates golden dataset + evalsets |

When business rules are in the spec, code generation reaches 90-95%. When omitted, 80% scaffolding with stubs.

### Layer 2 — Architecture Advisory (Blueprint Advisor MCP Server)

> For wire-level API details of internal RAG tools, see Operations Runbook, Section 1.

The Blueprint Advisor is an LlmAgent running on Cloud Run, **exposed as an MCP Server**. The coding agent connects via MCP protocol — the only universally compatible method (GitHub Copilot cannot make HTTP calls, but all major coding agents support MCP).

**MCP Tools exposed to the coding agent:**

| MCP Tool | Type | Purpose |
|---|---|---|
| `recommend_architecture(spec, plan)` | **ADVISORY** (non-deterministic) | Blueprint Advisor LlmAgent runs internally: searches catalogs via RAG, reasons about architecture, returns recommendations with confidence scores |
| `validate_composition(pattern_tree)` | **DETERMINISTIC** | Checks developer's edited selections against adjacency matrix |
| `assemble_blueprint(selections, spec, plan)` | **DETERMINISTIC** | Builds final YAML from validated selections. No LLM involved. |

**MCP protocol version:** 2025-03-26 (tested with Copilot, Claude Code, Cursor; community-tested with Gemini CLI, Windsurf).

**Blueprint Advisor versioning:** Every YAML includes version metadata:

```yaml
# Generated by: blueprint-advisor/v2.3.1
# System prompt: v1.8 (SHA: abc123)
# Pattern catalog: 2026-05-10 (11 patterns)
```

**Internal to the MCP Server (NOT exposed to the coding agent):**

| Internal Component | Purpose |
|---|---|
| Blueprint Advisor LlmAgent | RAG + LLM reasoning guided by company system prompt |
| `search_patterns()` / `search_skills()` / `search_tools()` | RAG tools — query Vertex AI Search data stores |
| Company system prompt | Curated best practices, constraints, preferences |
| Vertex AI Search connections | 3 data stores (patterns, skills, tools) |

The coding agent has no direct access to Vertex AI Search, the system prompt, or the LlmAgent. All intelligence lives on the server side.

**`/catalyst.blueprint` command flow:**

1. Coding agent calls `recommend_architecture(spec, plan)` via MCP
2. MCP Server runs Blueprint Advisor LlmAgent internally
3. Returns recommendations with confidence scores
4. Developer reviews, edits selections
5. Coding agent calls `validate_composition(edited_pattern_tree)` — deterministic
6. Coding agent calls `assemble_blueprint(validated_selections, spec, plan)` — deterministic
7. Result: `app-blueprint.yaml` written to workspace

**Offline / disconnected fallback:** If the MCP Server is unreachable, the developer can write `app-blueprint.yaml` manually using the YAML schema and FNOL example (Appendix A.10) as a template. `/catalyst.generate` only needs the YAML file — it does not require the MCP Server.

### Blueprint Advisor MCP Server — Security

| Concern | Control |
|---|---|
| Authentication | OAuth 2.0 via company SSO. Per-user identity. Workload Identity Federation. |
| Transport | TLS 1.3 (Cloud Run default). All MCP connections encrypted. |
| Spec content handling | Processed in-memory only. NOT persisted on server. NOT logged. Only spec hash (SHA-256) captured in telemetry. |
| Data residency | Spec content stays within configured GCP region. |
| Credential provisioning | MCP endpoint + OAuth client ID configured in `preset.yml`. First-time OAuth browser flow. Silent token refresh. |

> Transport security details (hop-by-hop encryption, audit trail schema) are in the Operations Runbook, Section 1.

### Blueprint Advisor MCP Server — Capacity and Rate Limiting

| Limit | Value | Rationale |
|---|---|---|
| Per-developer | 10 calls/hour | Developers rarely need more than 3-5 iterations |
| Per-team | 30 calls/hour | Prevents monopolization |
| Concurrent | 5 simultaneous `recommend_architecture` calls | Each holds an instance for 15-30s |
| `validate_composition` / `assemble_blueprint` | No limit | Sub-second, negligible cost |

Monthly Blueprint Advisor cost at expected usage (10-20 developers): **$12–25/month** (included in $1K/month GCP estimate).

> See Operations Runbook, Section 9 for Cloud Run scaling configuration.

### Layer 3 — Skill-Guided Code Generation

> For complete code generation walkthrough with directory trees, see Developer Guide, Section 2.

The coding agent reads the YAML blueprint and generates the complete project, constrained by:

| Layer | Source | Role |
|---|---|---|
| **Blueprint** (WHAT) | `app-blueprint.yaml` from Blueprint Advisor | Topology, tool assignments, infrastructure |
| **Archetype skill** (HOW) | `adk-agents` SKILL.md | Framework-specific patterns, imports, constructors |
| **Overlay skills** (MUST) | Company SKILL.md files | Non-negotiable standards (Terraform, Dynatrace, CI/CD, security) |
| **Constitution.md** | In the preset | Non-negotiable coding rules (NOT meta-skills — those exist only in AgentForge) |

**FORBIDDEN commands — three-layer enforcement:**

| Layer | Enforcement |
|---|---|
| Skill instruction | company-cicd skill: "Generate pipeline files. NEVER deploy directly." |
| Constitution rule | constitution.md: "NEVER run `agents-cli eval`, `agents-cli simulate`, or `agents-cli deploy`." |
| CLI override | `.agentcli-overrides.yaml` disables eval/simulate/deploy at the CLI level |

Even if the coding agent's LLM "decides" to deploy, the CLI-level override prevents execution. Defense in depth.

**What code generation produces (80-95% depending on business rules in spec):**

| Generated | Source (YAML) |
|---|---|
| ADK agent class hierarchy | `agents:` |
| MCP server connections | `tools.mcp_servers:` |
| A2A client connections | `tools.a2a_agents:` |
| FunctionTool implementations (first draft from business rules) | `tools.function_tools:` + `business_rules:` |
| Terraform modules | `infrastructure:` |
| Dynatrace + Splunk config | `observability:` |
| Jenkins + Harness pipelines | `ci_cd:` |
| Model Armor callbacks | `security:` |
| Pre-commit hook + Phoenix + golden dataset + 3-phase Harness eval | `evalops:` + `golden_dataset:` |

**What the developer implements (5-20%):** System prompts (P0), review first-draft FunctionTool logic (P0), eval dataset curation (P1), proprietary algorithms not expressible as IF/THEN (P1), Pydantic schemas (P2).

### Layer 4 — Company CI/CD

> For EvalOps maintenance procedures, see Operations Runbook, Section 8.

| Pipeline | Tool | Purpose |
|---|---|---|
| Infrastructure | Jenkins | `terraform plan` → `terraform apply` → Cloud Run, Apigee, Cloud SQL, Model Armor, VPC-SC |
| Application | Harness | Deploy → 3-phase EvalOps → Non-Prod → Pre-Prod (canary) → Production |

**EvalOps — three-layer evaluation lifecycle:**

| Layer | What | When |
|---|---|---|
| **Layer 1: Inner Loop** | Pre-commit hook, 5-10 evalsets in <60s. Blocks on >10% regression. | Before `git commit` |
| **Layer 2: Deep Dive** | ADK tracing + Arize Phoenix. Explains WHY agents fail. | Local dev + deployed |
| **Layer 3: Outer Loop** | 3-phase Harness: Arize gates → AutoSxS baseline → HITL triage | CI/CD pipeline |

Note: `agents-cli eval` is FORBIDDEN. All evaluation uses pre-commit hook (Layer 1) + Harness pipeline (Layer 3).

**Golden dataset quality gate (enforced by pre-commit hook):**

| Check | Minimum | What it catches |
|---|---|---|
| Total entries | ≥ 10 per agent | Low-coverage datasets |
| Edge cases | ≥ 3 | Happy-path-only datasets |
| Negative tests | ≥ 1 (expected failure) | Missing error handling verification |
| Agent coverage | 100% of agents in blueprint | Agents with zero evaluation |

**Golden dataset lifecycle:** Acceptance criteria → starter dataset → developer curation → production feedback (drift → annotation → update) → quarterly meta-evaluation (≥85% agreement threshold).

### Layer 5 — Runtime & Operate

All runtime services are GA with SLA backing:

| Component | Service |
|---|---|
| Agent runtime | Cloud Run (GA) |
| API Gateway | Apigee Runtime Gateway (GA) |
| Content screening | Model Armor (standard — segmented is future roadmap; requires custom implementation beyond the API) |
| Observability | Dynatrace + Splunk + OTel Collector |
| Security | VPC-SC + CMEK + Secret Manager + Workload Identity |

---

## Governance Model

| Component | Owner |
|---|---|
| AgentCatalyst platform + Blueprint Advisor MCP Server | Platform Engineering |
| Pattern catalog + overlay skills | Platform Engineering |
| FORBIDDEN command enforcement (three-layer override) | Platform Engineering |
| Individual use cases | LOB development teams |
| CI/CD pipelines | DevOps / Platform Engineering |

---

## What AgentCatalyst is NOT

- **Not a deployment tool.** Generates code and pipeline definitions. Your CI/CD deploys. `agents-cli deploy` is FORBIDDEN.
- **Not a hosting platform.** Cloud Run + Apigee hosts your agents.
- **Not a replacement for developers.** Generates 80-95%. Developers review, refine, and own the code.
- **Not AgentForge.** AgentForge uses meta-skills + signed Design Contracts + attestation chains. AgentCatalyst uses Blueprint Advisor RAG + skill-constrained generation. Zero IP overlap.
- **Not archetype-agnostic in this variant.** This agents-cli variant is agentic-only. For multi-archetype support (microservices, pipelines, APIs), use the GA variant with preset-swapping.

---

## Risks and Mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | Blueprint Advisor recommends wrong pattern | Confidence scores in YAML. `validate_composition` catches invalid nesting. Rate limited to 10 calls/hr. |
| 2 | Developer bypasses FORBIDDEN commands | Three-layer enforcement (skill + constitution + CLI override). Defense in depth. |
| 3 | Stale catalogs | Weekly health checks. Regression suite. GitHub repos as source of truth with DR procedure. See Ops Runbook. |
| 4 | agents-cli CLI changes | Used only for scaffolding (one-time). Runtime is GA-only. Low risk. |
| 5 | MCP Server unreachable | Offline fallback: manual YAML authoring with FNOL example as template. `validate_composition` + `assemble_blueprint` may still work. |
| 6 | Spec content security | OAuth 2.0 auth, TLS 1.3 transport, spec NOT persisted on server, data stays in GCP region. |

---

## Production Readiness Checklist

| # | Check | Status |
|---|---|---|
| 1 | All overlay skills pinned to specific versions | ⬜ |
| 2 | Blueprint Advisor MCP Server deployed with OAuth 2.0 + TLS 1.3 | ⬜ |
| 3 | Vertex AI Search data stores populated (≥80% search precision) | ⬜ |
| 4 | Company system prompt reviewed by EA + Security | ⬜ |
| 5 | Constitution.md reviewed (includes FORBIDDEN commands) | ⬜ |
| 6 | `.agentcli-overrides.yaml` disables eval/simulate/deploy | ⬜ |
| 7 | Three-layer FORBIDDEN enforcement tested end-to-end | ⬜ |
| 8 | Pre-commit hook + golden dataset quality gate tested | ⬜ |
| 9 | 3-phase Harness evaluation pipeline tested | ⬜ |
| 10 | FNOL reference implementation passing all gates | ⬜ |
| 11 | Catalog DR procedure documented and tested (RTO < 4 hours) | ⬜ |
| 12 | Rate limiting configured (10/hr per-dev, 5 concurrent) | ⬜ |

---

## Related Documents

| Document | Audience | What it covers |
|---|---|---|
| **This Architecture Document** | Architects | WHY — decisions, MCP Server design, FORBIDDEN enforcement, security, capacity |
| **AgentCatalyst Developer Guide** (agents-cli) | Developers | HOW — greenfield FNOL walkthrough, spec writing, EvalOps (no `agents-cli eval`), troubleshooting |
| **AgentCatalyst Operations Runbook** | Platform eng | PROCEDURES — wire-level APIs, regression testing, telemetry, catalog DR, failure modes, MCP Server ops |

*The Operations Runbook applies to both GA and agents-cli variants — all operational procedures are platform-level.*

---

## Appendix A — FNOL Agentic Application: Complete Preset & Example Files

*This appendix contains all files used in the FNOL (First Notice of Loss) agentic application example referenced throughout this document. These files constitute the AgentCatalyst preset for the agentic archetype.*

### Directory structure

```
.specify/
├── preset.yml                              ← Manifest: archetype, templates, commands, settings
├── templates/
│   ├── spec-template.md                    ← /specify loads this — 10-section structured format
│   ├── plan-template.md                    ← /plan loads this — technical questions
│   └── tasks-template.md                   ← /tasks loads this — generated vs manual work
├── commands/
│   ├── catalyst.blueprint.md               ← Connects to Blueprint Advisor MCP Server, calls recommend_architecture
│   └── catalyst.generate.md                ← Custom command: reads YAML, triggers skill-guided generation
├── memory/
│   ├── adk-reference.md                    ← ADK framework patterns, imports, constructors
│   ├── company-patterns.md                 ← Company coding standards, naming, error handling
│   ├── approved-tools.md                   ← Approved MCP servers, A2A endpoints, FunctionTools
│   └── infra-standards.md                  ← Terraform modules, Dynatrace config, CI/CD templates
└── constitution.md                         ← Non-negotiable rules the coding agent MUST follow
```

---

### A.1 preset.yml

```yaml
# AgentCatalyst Preset for GitHub Spec Kit
# Install: specify preset add agentcatalyst-enterprise
# Source: github.com/[company]/agentcatalyst-preset

name: agentcatalyst
version: "1.0.0"
description: >
  AgentCatalyst enterprise agent development accelerator.
  Structured requirements capture, AI-assisted architecture advice
  via Blueprint Advisor, and skill-guided code generation.

archetype: agentic    # Also available: microservice, pipeline, api

templates:
  spec: templates/spec-template.md
  plan: templates/plan-template.md
  tasks: templates/tasks-template.md

commands:
  - commands/catalyst.blueprint.md
  - commands/catalyst.generate.md

memory:
  - memory/adk-reference.md
  - memory/company-patterns.md
  - memory/approved-tools.md
  - memory/infra-standards.md

skills:
  domain:
    - name: adk-agents
      version: "1.2.0"
      source: github.com/[company]/skills/adk-agents
    - name: adk-tools
      version: "1.1.0"
      source: github.com/[company]/skills/adk-tools
  overlay:
    - name: company-terraform
      version: "2.0.0"
      source: github.com/[company]/skills/company-terraform
    - name: company-observability
      version: "1.3.0"
      source: github.com/[company]/skills/company-observability
    - name: company-cicd
      version: "1.5.0"
      source: github.com/[company]/skills/company-cicd
    - name: company-security
      version: "1.2.0"
      source: github.com/[company]/skills/company-security

settings:
  coding_agents: [copilot, claude-code, gemini-cli, cursor, windsurf]
  output_format: markdown
  save_location: workspace_root
```

---

### A.2 templates/spec-template.md

```markdown
---
template: agentcatalyst-spec
version: "1.0.0"
description: Structured requirements for agentic AI applications
usage: Run /specify to fill in this template
---

# Agent Specification

## Business Problem

<!--
Describe who uses this agent, what it automates, and the business value.
EXAMPLE: "We need an AI agent that handles FNOL for auto insurance.
When a policyholder reports an accident, the agent verifies coverage,
collects details, assesses severity, and routes high-severity to adjusters.
Currently takes 3-5 days. Target: under 1 hour."
-->

[Describe your business problem here]

## Workflow

<!--
Step-by-step workflow using ordering words that guide pattern selection:
- "First... Then... Finally" → Sequential
- "Simultaneously... In parallel" → Parallel
- "Generate... validate... refine until" → Loop
- "If [condition], route to [role]" → HITL
-->

[Describe your workflow here]

## Data Sources

<!--
List every data system with access pattern and workload type:
- "BigQuery policy warehouse (analytical, read-only)" → BigQuery MCP
- "Cloud SQL active claims (transactional, read-write)" → Cloud SQL MCP
- "Policy documents in GCS (retrieval)" → Vertex AI Search
-->

[List your data sources here]

## External Integrations

<!--
Partner services you DON'T operate. Use "they operate their own"
to signal A2A agent connections vs MCP tool connections.
EXAMPLE: "Body shop network — they operate their own scheduling system"
-->

[List external integrations here]

## Internal Capabilities

<!--
Proprietary logic YOUR team owns. These become FunctionTool implementations.
Describe each as structured IF/THEN rules where possible.
EXAMPLE: "Severity classifier — IF vehicle_damage > $10K AND injuries = true
THEN severity = 'high' AND route_to_adjuster = true"
-->

[List internal capabilities here]

## Infrastructure Requirements

<!--
GCP region, compliance, data residency, networking constraints.
Check memory/infra-standards.md for approved Terraform module versions.
-->

[Describe infrastructure requirements here]

## Business Rules

<!--
Structured IF/THEN conditions per decision point. These generate
first-draft FunctionTool implementations that you review and refine.

FORMAT:
Decision Point: [name]
  Inputs: [what data feeds this decision]
  IF [condition] THEN [action]
  IF [condition] THEN [action]
  ELSE [default action]
  Edge cases: [what happens with missing/invalid data]
  Validation: [how to verify correctness]
-->

[Define your business rules here]

## Transformation Rules

<!--
Field mappings and formulas for data transformations.
FORMAT:
Source: [field_name from system_name]
Target: [output_field_name]
Formula: [transformation logic]
-->

[Define your transformation rules here]

## Error Handling

<!--
Per-dependency timeout, failure, and retry behavior.
FORMAT:
Dependency: [system_name]
  Timeout: [duration]
  On failure: [retry N times / fail open / fail closed / use cached]
  On partial data: [proceed with available / block until complete]
-->

[Define your error handling here]

## Acceptance Criteria

<!--
GIVEN/WHEN/THEN assertions per workflow step. These generate
the starter golden dataset for EvalOps evaluation.

FORMAT:
GIVEN [precondition]
WHEN [action/trigger]
THEN [expected outcome]
AND [additional assertion]
-->

[Define your acceptance criteria here]
```

---

### A.3 templates/plan-template.md

```markdown
---
template: agentcatalyst-plan
version: "1.0.0"
description: Technical decisions mapping to blueprint fields
usage: Run /plan to answer these questions
---

# Technical Plan

## Target Platform
- **Runtime:** [cloud_run]
- **GCP Project:** [project-id]
- **GCP Region:** [e.g., us-central1]

## Model Selection
- **Primary model:** [e.g., gemini-2.0-flash]
- **Reasoning model (if different):** [e.g., gemini-2.0-pro for complex steps]

## Infrastructure
- **Terraform module source:** [e.g., github.com/[company]/terraform-modules]
- **Terraform module version:** [e.g., v3.2.1]
- **VPC-SC perimeter:** [yes/no]
- **CMEK encryption:** [yes/no]

## CI/CD
- **Infrastructure pipeline:** [Jenkins]
- **Application pipeline:** [Harness]
- **Deployment strategy:** [canary/blue-green/rolling]
- **Canary percentage:** [e.g., 10%]
- **Observation window:** [e.g., 30 minutes]

## Observability
- **APM:** [Dynatrace]
- **SIEM:** [Splunk]
- **Tracing:** [OpenTelemetry + Arize Phoenix]

## Security
- **Model Armor:** [standard]
- **DLP scanning:** [yes/no]
- **Secret Manager:** [yes/no — for API keys, credentials]

## EvalOps
- **Pre-commit threshold:** [e.g., 10% max regression]
- **Arize pass_rate gate:** [e.g., >= 0.95]
- **Arize p95_latency gate:** [e.g., <= 3s]
- **HITL routing condition:** [e.g., confidence < 0.7 or edge_case = true]
```

---

### A.4 templates/tasks-template.md

```markdown
---
template: agentcatalyst-tasks
version: "1.0.0"
description: Task breakdown — generated vs developer-implemented
usage: Run /tasks after receiving blueprint to see the breakdown
---

# Task Breakdown

## Generated by coding agent (developer reviews)

| Component | Source (YAML section) | Status |
|---|---|---|
| ADK agent class hierarchy | agents: | ⬜ Generated |
| MCP server connections | tools.mcp_servers: | ⬜ Generated |
| A2A client connections | tools.a2a_agents: | ⬜ Generated |
| FunctionTool implementations (first draft from business rules) | tools.function_tools: + business_rules: | ⬜ Generated — REVIEW REQUIRED |
| Terraform modules | infrastructure: | ⬜ Generated |
| Dynatrace observability config | observability: | ⬜ Generated |
| Jenkins + Harness pipelines | ci_cd: | ⬜ Generated |
| Model Armor callbacks | security: | ⬜ Generated |
| Pre-commit evaluation hook | evalops: | ⬜ Generated |
| Arize Phoenix tracing config | evalops: | ⬜ Generated |
| Golden dataset (starter) | golden_dataset: | ⬜ Generated |
| 3-phase Harness eval pipeline | evalops: | ⬜ Generated |

## Developer implements / reviews

| Task | Why it can't be generated | Priority |
|---|---|---|
| Review FunctionTool business logic | First draft generated from spec rules — developer refines and makes it their own | P0 |
| System prompts per agent | Requires domain expertise, tone, persona | P0 |
| Eval dataset curation | Requires real-world edge cases beyond acceptance criteria | P1 |
| Proprietary algorithms | ML models, actuarial formulas not expressible as IF/THEN | P1 |
| Pydantic output schemas | Domain-specific data contracts | P2 |
```

---

### A.5 commands/catalyst.blueprint.md

```markdown
---
name: catalyst.blueprint
description: Connect to Blueprint Advisor MCP Server for architecture recommendation
usage: /catalyst.blueprint
---

# /catalyst.blueprint

Read `spec.md` and `plan.md` from the current workspace.

Connect to the Blueprint Advisor MCP Server:
  endpoint: mcp://blueprint-advisor.[company-domain].run.app
  auth: OAuth 2.0 (company SSO)

Call the `submit_spec_and_plan` MCP tool with:
  - spec: contents of spec.md
  - plan: contents of plan.md
  - archetype: from preset.yml (e.g., "agentic")

The MCP server internally runs the Blueprint Advisor LlmAgent:
  1. Queries Vertex AI Search catalogs (patterns, skills, tools)
  2. Applies LLM reasoning guided by company system prompt
  3. Assembles the blueprint YAML
  4. Returns the result via MCP protocol

The coding agent CANNOT access Vertex AI Search directly.
The coding agent CANNOT invoke the LlmAgent directly.
All intelligence lives on the server side, accessed only via MCP tools.```

Connect to the Blueprint Advisor MCP Server:
`mcp://blueprint-advisor.[company-domain].run.app`

Call the `submit_spec_and_plan` MCP tool with the spec and plan contents.
The MCP server handles all internal processing (RAG search, LLM reasoning, blueprint assembly) and returns the result.

Save the response as `app-blueprint.yaml` in the workspace root.

Display a summary showing:
- Number and types of agents recommended
- Number of MCP servers, A2A agents, and FunctionTool implementations
- Skills discovered with versions
- Confidence level (high/medium/low) for each recommendation

Remind the developer: "Review the YAML and edit any field before running /catalyst.generate."
```

---

### A.6 commands/catalyst.generate.md

```markdown
---
name: catalyst.generate
description: Read the YAML blueprint and generate the complete project using skills
usage: /catalyst.generate
---

# /catalyst.generate

Read `app-blueprint.yaml` from the workspace root.

Validate the YAML schema:
- All required fields present (archetype, agents[], tools, infrastructure)
- All referenced skills available in the preset
- Pattern composition is valid (no forbidden nesting)

Load skills in this order:
1. constitution.md (non-negotiable rules — read FIRST)
2. Archetype skill (e.g., adk-agents) — teaches framework-specific patterns
3. Company overlay skills (terraform, observability, cicd, security) — teaches company standards

Generate the complete project following the blueprint:
- For each agent in agents[]: generate ADK class file
- For each MCP server: generate connection file
- For each A2A agent: generate client file
- For each FunctionTool: generate implementation file with first-draft business logic from business_rules
- Generate Terraform modules from infrastructure section
- Generate observability config from observability section
- Generate CI/CD pipelines from ci_cd section
- Generate Model Armor callbacks from security section
- Generate pre-commit evaluation hook from evalops section
- Generate Phoenix tracing config from evalops section
- Generate golden dataset from golden_dataset section
- Generate 3-phase Harness evaluation pipeline from evalops section

Commit all generated files to the workspace.

CRITICAL: Do NOT deploy. Do NOT run `terraform apply`. Do NOT run `agents-cli deploy`.
Generate pipeline FILES. The company's CI/CD will deploy after the developer commits and opens a PR.
```

---

### A.7 memory/ files (summaries)

**memory/adk-reference.md** — ADK framework reference loaded into the coding agent's context. Contains correct import paths (`from google.adk import Agent`), class constructors for all ADK agent types (LlmAgent, SequentialAgent, ParallelAgent, LoopAgent), tool wiring patterns, MCP connection boilerplate, A2A client patterns, and common pitfalls to avoid.

**memory/company-patterns.md** — Company coding standards loaded into the coding agent's context. Contains naming conventions (snake_case for files, PascalCase for classes), error handling standards (structured logging, retry with exponential backoff), code organization patterns (agents in `app/sub_agents/`, tools in `app/tools/`, MCP in `app/mcp_connections/`), and documentation requirements (docstrings on all public functions).

**memory/approved-tools.md** — Registry of approved MCP servers, A2A endpoints, and FunctionTool patterns. Each entry includes the tool name, endpoint URL, connection type (MCP/A2A/FunctionTool), capabilities description, assigned data domain, and SLA. The coding agent checks this list before generating tool connections.

**memory/infra-standards.md** — Infrastructure standards loaded into the coding agent's context. Contains approved Terraform module versions (pinned), Dynatrace dashboard-as-code templates, Jenkins pipeline template paths, Harness pipeline template structure, VPC-SC perimeter rules, CMEK key ring references, and Cloud Run scaling parameters.

---

### A.8 constitution.md (key rules)

```markdown
---
name: agentcatalyst-constitution
description: Non-negotiable rules for the coding agent
---

# Constitution

## MUST follow (non-negotiable)

1. NEVER deploy directly. Generate pipeline files only. The company's CI/CD deploys.
2. NEVER create resources outside the approved GCP project.
3. ALWAYS use company Terraform modules — never raw GCP provider resources.
4. ALWAYS use approved Dynatrace dashboard templates — never custom dashboards.
5. ALWAYS generate pre-commit evaluation hooks and golden dataset.
6. ALWAYS use company naming conventions (see memory/company-patterns.md).
7. NEVER hardcode secrets — use Secret Manager references.
8. ALWAYS generate Model Armor callbacks for every agent.
9. ALWAYS include VPC-SC configuration when security.vpc_sc = true.
10. ALWAYS generate 3-phase Harness evaluation pipeline (Arize → AutoSxS → HITL).

## SHOULD follow (best practice)

1. Prefer FunctionTool with business logic from spec over empty stubs.
2. Include retry logic with exponential backoff for all external calls.
3. Add structured logging at every agent decision point.
4. Generate Pydantic models for all tool input/output schemas.
5. Include health check endpoints for every deployed service.
```

---

### A.9 FNOL Example: Filled spec.md

```markdown
# Agent Specification — FNOL (First Notice of Loss)

## Business Problem

We need an AI agent that handles First Notice of Loss (FNOL) for auto insurance.
When a policyholder reports an accident via phone or web, the agent should verify
their policy, collect incident details, assess severity, and either auto-approve
low-severity claims or route high-severity ones to a human adjuster. Currently
this process takes 3-5 days manually. The agent should reduce it to under 1 hour.

## Workflow

1. First, verify the policyholder's identity and active coverage by
   querying our BigQuery policy data warehouse.
2. Then, extract structured incident details from the caller's description.
3. After extraction, simultaneously enrich with three external sources:
   body shop repair estimates, rental car availability, police report.
4. Generate a claim summary, validate against our quality rubric, and
   refine until the quality score exceeds 0.85.
5. If severity is high or fraud score > 0.7, route to a human adjuster
   for review and approval.

## Data Sources

- BigQuery policy data warehouse (analytical, read-only) — coverage verification
- Cloud SQL active claims database (transactional, read-write) — claim creation and updates
- Vertex AI Search policy documents (retrieval) — policy terms and conditions

## External Integrations

- Body shop network — they operate their own scheduling and estimation system
- Rental car service — they operate their own fleet availability API
- Police report service — they operate their own incident report retrieval

## Internal Capabilities

- Severity classifier — our proprietary algorithm that assesses claim severity
- Coverage calculator — determines deductible and coverage limits per policy type
- Notification sender — sends status updates to policyholder via email/SMS

## Infrastructure Requirements

- GCP region: us-central1
- Data residency: US only
- VPC-SC perimeter required
- CMEK encryption for all data at rest

## Business Rules

Decision Point: Severity Classification
  Inputs: vehicle_damage_estimate, injury_reported, num_vehicles, police_report_filed
  IF vehicle_damage > $10,000 AND injury_reported = true THEN severity = "critical"
  IF vehicle_damage > $10,000 AND injury_reported = false THEN severity = "high"
  IF vehicle_damage > $2,000 THEN severity = "medium"
  ELSE severity = "low"
  Edge cases: IF vehicle_damage is unknown, default to severity = "high" (conservative)

Decision Point: Fraud Routing
  Inputs: fraud_risk_score, claim_frequency_last_12mo, police_report_consistent
  IF fraud_risk_score > 0.7 THEN route_to_siu = true
  IF claim_frequency_last_12mo > 3 THEN flag_for_review = true
  IF police_report_consistent = false THEN escalate_to_adjuster = true

## Transformation Rules

Source: caller_description (free text)
Target: structured_incident (JSON)
Formula: Extract date, time, location, vehicles involved, injuries, description using LLM

Source: policy_record (BigQuery row)
Target: coverage_summary (JSON)
Formula: Map policy_type to deductible schedule, calculate remaining coverage = max_coverage - ytd_claims

## Error Handling

Dependency: BigQuery policy warehouse
  Timeout: 5 seconds
  On failure: Retry 3 times with exponential backoff. If still failing, proceed with cached policy data (stale up to 24 hours).
  On partial data: Proceed with available fields, flag missing fields in claim summary.

Dependency: Body shop network API
  Timeout: 10 seconds
  On failure: Retry 2 times. If still failing, skip enrichment and flag "estimate pending" in claim.
  On partial data: Use available estimate, note confidence = "partial".

## Acceptance Criteria

GIVEN a policyholder with active policy P-12345
WHEN they report a minor fender bender with $1,500 damage and no injuries
THEN severity = "low" AND auto_approved = true AND adjuster_review = false

GIVEN a policyholder with active policy P-67890
WHEN they report a multi-vehicle accident with $25,000 damage and injuries
THEN severity = "critical" AND route_to_adjuster = true AND priority = "urgent"

GIVEN a caller with no matching policy
WHEN they attempt to file a claim
THEN claim_rejected = true AND reason = "no active policy" AND redirect_to_sales = true
```

---

### A.10 FNOL Example: Generated app-blueprint.yaml

```yaml
# Generated by Blueprint Advisor
# Spec: spec.md (SHA: abc123)
# Plan: plan.md (SHA: def456)
# Generated: 2026-05-10T14:30:00Z

archetype: agentic

agents:
  - name: fnol_coordinator
    type: LlmAgent
    model: gemini-2.0-flash
    role: Root coordinator for FNOL claim processing
    sub_agents: [intake_pipeline, enrichment_parallel, summary_loop, adjuster_review]

  - name: intake_pipeline
    type: SequentialAgent
    steps: [verify_coverage, extract_details]
    role: Sequential intake — verify then extract

  - name: enrichment_parallel
    type: ParallelAgent
    branches: [body_shop_enrichment, rental_car_enrichment, police_report_enrichment]
    role: Parallel enrichment from 3 external sources

  - name: summary_loop
    type: LoopAgent
    max_iterations: 3
    exit_condition: quality_score >= 0.85
    role: Generate and refine claim summary until quality threshold

  - name: adjuster_review
    type: LlmAgent
    role: Human-in-the-loop — routes high severity to adjuster

tools:
  mcp_servers:
    - name: bigquery-policy
      endpoint: mcp://bigquery.internal:8443
      assigned_to: verify_coverage
      capabilities: Query policy data warehouse

    - name: cloud-sql-claims
      endpoint: mcp://cloudsql-claims.internal:8443
      assigned_to: fnol_coordinator
      capabilities: Create and update claim records

    - name: vertex-search-policies
      endpoint: mcp://vertex-search.internal:8443
      assigned_to: verify_coverage
      capabilities: Search policy terms and conditions

  a2a_agents:
    - name: body-shop-network
      agent_card: https://bodyshop-agent.partner.com/.well-known/agent.json
      assigned_to: body_shop_enrichment
      capabilities: Get repair estimates and scheduling

    - name: rental-car-service
      agent_card: https://rental-agent.partner.com/.well-known/agent.json
      assigned_to: rental_car_enrichment
      capabilities: Check fleet availability and pricing

    - name: police-report-service
      agent_card: https://police-report.gov/.well-known/agent.json
      assigned_to: police_report_enrichment
      capabilities: Retrieve incident reports by case number

  function_tools:
    - name: severity_classifier
      assigned_to: fnol_coordinator
      description: Classify claim severity based on damage, injuries, vehicles
      business_rules:
        - "IF vehicle_damage > $10,000 AND injury_reported = true THEN severity = critical"
        - "IF vehicle_damage > $10,000 AND injury_reported = false THEN severity = high"
        - "IF vehicle_damage > $2,000 THEN severity = medium"
        - "ELSE severity = low"
        - "Edge: IF vehicle_damage unknown THEN severity = high (conservative)"

    - name: coverage_calculator
      assigned_to: verify_coverage
      description: Calculate deductible and remaining coverage
      business_rules:
        - "Map policy_type to deductible schedule"
        - "remaining_coverage = max_coverage - ytd_claims"

    - name: notification_sender
      assigned_to: fnol_coordinator
      description: Send status updates to policyholder
      business_rules:
        - "IF severity = critical THEN notify via SMS + email immediately"
        - "IF severity = low AND auto_approved THEN notify via email within 1 hour"

skills:
  - name: adk-agents
    version: "1.2.0"
    provenance: github.com/[company]/skills/adk-agents@sha256:abc123

infrastructure:
  runtime: cloud_run
  region: us-central1
  terraform_module: github.com/[company]/terraform-modules@v3.2.1
  vpc_sc: true
  cmek: true

observability:
  apm: dynatrace
  siem: splunk
  tracing: opentelemetry + arize-phoenix

security:
  model_armor: standard
  dlp: true
  secret_manager: true

evalops:
  pre_commit_threshold: 0.10
  arize_pass_rate: 0.95
  arize_p95_latency: 3.0
  hitl_routing: "confidence < 0.7 OR edge_case = true"

golden_dataset:
  - given: "policyholder with active policy P-12345"
    when: "minor fender bender, $1500 damage, no injuries"
    then: "severity=low, auto_approved=true, adjuster_review=false"
  - given: "policyholder with active policy P-67890"
    when: "multi-vehicle, $25000 damage, injuries"
    then: "severity=critical, route_to_adjuster=true, priority=urgent"
  - given: "caller with no matching policy"
    when: "attempt to file claim"
    then: "claim_rejected=true, reason=no_active_policy"

ci_cd:
  infra_pipeline: jenkins
  app_pipeline: harness
  deployment_strategy: canary
  canary_percentage: 10
  observation_window_minutes: 30

patterns_used:
  - pattern: coordinator
    confidence: high
    rationale: "Multiple specialized sub-agents coordinated by root"
  - pattern: sequential
    confidence: high
    rationale: "Workflow says 'First...Then' for intake steps"
  - pattern: parallel
    confidence: high
    rationale: "Workflow says 'simultaneously' for enrichment"
  - pattern: loop
    confidence: high
    rationale: "Workflow says 'refine until quality score exceeds 0.85'"
  - pattern: hitl
    confidence: high
    rationale: "Workflow says 'route to human adjuster for review'"
```

*End of Appendix A*
