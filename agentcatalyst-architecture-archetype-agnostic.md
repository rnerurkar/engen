# AgentCatalyst — GA Architecture

**A spec-driven enterprise application development accelerator on Google Cloud Platform**
*GA-Only — all services SLA-backed, zero preview dependencies*

> **Note:** This document contains Mermaid.js diagrams in fenced code blocks. To render them as images, use a Mermaid-compatible viewer (VS Code with Mermaid Preview extension, GitHub, or mermaid.live). Standard markdown viewers will display the diagram source code instead.

---

## Executive Summary — For the SLT

### The problem

Every enterprise team building AI agents (or microservices, or data pipelines) today follows its own approach. Copilot helps write code faster, but it has no knowledge of company patterns, no understanding of compliance standards, and no ability to recommend architectures from organizational catalogs. The result: 50 teams produce 50 different implementations, 82 hours of compliance rework per use case, and 30+ POCs that never reach production.

### The solution: AgentCatalyst

AgentCatalyst is a spec-driven development accelerator with three core capabilities:

1. **Blueprint Advisor** — an LlmAgent exposed as an MCP Server that recommends architectures by searching company-curated catalogs via RAG. The developer's coding agent connects via MCP protocol, calls `blueprint_start(spec, plan)` to initiate an async task, polls for progress via `blueprint_status`, and retrieves the markdown blueprint via `blueprint_result` when complete. This async pattern (using MCP Tasks) is necessary because VS Code Copilot enforces a hard 10–15 second timeout on synchronous MCP tool calls, while the LlmAgent pipeline takes 15–60 seconds. The developer reviews and edits the blueprint — the human is always in control.

2. **Preset-based archetype adaptation** — each application type (agentic AI, microservice, data pipeline, API-first) is served by a self-contained preset with archetype-specific templates, catalogs, and skills. All presets share company overlay skills (Terraform, observability, CI/CD, security) maintained once by the platform team. New archetype = new preset. Zero platform changes.

3. **Skill-constrained code generation** — the coding agent (Copilot, Claude Code, Cursor) is constrained by three layers: the blueprint (WHAT), the archetype skill (HOW), and the overlay skills (MUST). Constitution.md encodes non-negotiable code generation rules. The coding agent generates a first draft of the complete application — including working business logic from structured rules in the spec — for the developer to review and make their own.

AgentCatalyst does NOT deploy agents. It generates code, infrastructure definitions, and CI/CD pipeline files — then commits everything to the developer's GitHub repo. The company's existing Jenkins + Harness pipelines take it to production.

![AgentCatalyst — How It Works](AgentCatalyst-SLT-Interaction-Diagram.png)

### AgentCatalyst at a glance

| Activity | Without AgentCatalyst | With AgentCatalyst | Improvement |
|---|---|---|---|
| Requirements capture | 3–5 days (meetings + documents) | 2–4 hours (/specify template) | 90% faster |
| Architecture design | 1–2 weeks (manual research) | 1–5 minutes (Blueprint Advisor) | 99% faster |
| Code generation | 1–2 weeks (manual project setup) | 5–10 minutes (skill-guided) | 99% faster |
| Infrastructure as code | 3–5 days (manual Terraform) | Automatic (from blueprint) | 90% faster |

### Key principles

1. **Spec-driven, not prompt-driven.** Structured 10-section templates with business rules — not free-form chat prompts.
2. **AI-advised, human-decided.** The Blueprint Advisor recommends; the developer reviews and edits the blueprint. The human is always in control.
3. **Compliant by construction.** Company overlay skills teach the coding agent non-negotiable standards. Compliance is structural, not retrofitted.
4. **Archetype-agnostic.** Same platform, same flow, same overlay skills — regardless of whether you're building an AI agent, a microservice, a data pipeline, or an API.
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
| Enterprise ROI (build-cost only) | **48×** | $8.19M savings / $170K build + onboarding investment |
| **Year 1 full TCO** | **$688K** | Platform build $51K + platform ops ~$400K (2 FTE) + EA curation ~$100K (0.5 FTE) + GCP infra ~$18K + LOB onboarding $119K |
| **Year 1 ROI (full TCO)** | **~12×** | $8.19M savings / $688K total investment. Year 2+ improves as build costs amortize |
| Each additional LOB | **$17K** to onboard |
| Time to first agent | **~3.5 weeks** (down from ~7.5 weeks) |

### Cost to build and operate

| Component | One-time build | Recurring |
|---|---|---|
| Pattern Knowledge Base (11 agentic patterns + Vertex AI Search) | ~120 hours (platform eng) | ~10 hours/quarter (catalog maintenance) |
| Blueprint Advisor MCP Server (LlmAgent + system prompt + RAG + golden dataset) | ~50 hours (platform eng) | ~5 hours/quarter (prompt tuning) |
| Company overlay skills (Terraform, observability, CI/CD, security, EvalOps) | ~80 hours (platform eng) | ~10 hours/quarter (version updates) |
| Each additional archetype preset | ~40 hours | ~5 hours/quarter |
| GCP infrastructure (Blueprint Advisor API layer + pipeline on Cloud Run, AlloyDB Task Store, Vertex AI Search, Arize Phoenix) | — | ~$500–1,500/month |

### Per use case cost comparison (both sides use Copilot)

| | Without AgentCatalyst (Copilot + published standards) | With AgentCatalyst (Copilot + skills + Blueprint Advisor) |
|---|---|---|
| **Build phase** | 446 hrs (requirements 60 + standards learning 24 + architecture 60 + code 100 + prompts 35 + infra/CI/CD/obs/security 82 + testing 60 + deploy 25) | 138 hrs (requirements 60 + spec/plan/biz rules 8 + Blueprint Advisor 0.1 + generate 1 + complex domain logic 20 + prompts 25 + testing 15 + PR 8) |
| **Compliance remediation** | 82 hrs (EA review 16 + security review 16 + rework 50) | 0 hrs (compliant by construction — overlay skills enforce company standards; constitution.md constrains code generation) |
| **Total** | **528 hrs / $52.8K / ~7.5 weeks** | **138 hrs / $13.8K / ~3.5 weeks** |
| **Savings** | | **$39K per use case (74%)** |

† If business rules are NOT captured in the spec, add $5.5K per use case (55 hrs) for manual business logic implementation → $19.3K / 193 hrs per use case. Enterprise savings drop from $8.0M to $6.85M but ROI remains 36×.

Note: Requirements gathering (60 hrs) is identical on both sides. AgentCatalyst does not reduce the time to gather requirements — it reduces the time to go from requirements to production-ready code.

### Application archetypes — one platform, many application types

AgentCatalyst achieves archetype-agnosticism through preset-swapping, not meta-skills or signed contracts:

| Archetype | Preset Name | Spec Template | Catalog | Domain Skill | Status |
|---|---|---|---|---|---|
| **Agentic AI** | `agentcatalyst` | agent-spec-template.md | 11 ADK patterns | `adk-agents` | **Phase 1 — active** |
| **Microservice** | `agentcatalyst-microservice` | service-spec-template.md | Microservice patterns | `springboot-service` / `fastapi` | **Phase 2 — planned** |
| **Data Pipeline** | `agentcatalyst-pipeline` | pipeline-spec-template.md | ETL/ELT patterns | `beam` / `dataflow` | **Phase 3 — planned** |
| **API-First** | `agentcatalyst-api` | api-spec-template.md | API patterns | `openapi` / `graphql` | **Phase 4 — planned** |

All presets share the same company overlay skills: Terraform, Dynatrace, Jenkins/Harness, security, EvalOps. New archetype = new preset + new catalog + new domain skill. Zero overlay changes. Zero platform changes.

### GA-only commitment

Every GCP service used by AgentCatalyst is Generally Available with SLA backing. No preview APIs. No preview services. Deployable in any GCP project, including locked-down enterprise environments.

---

## End-to-end thread (read this first)

Before diving into the five layers, here is the complete flow as a narrative. No jargon, no architecture diagrams — just what happens step by step from the developer's perspective.

A developer is asked to build an AI agent that processes auto insurance claims (FNOL). She opens VSCode with her preferred coding agent — Claude Code, in her case — and installs the AgentCatalyst preset: `specify preset add agentcatalyst-enterprise`. This installs a structured spec template, a plan template, custom commands (`/catalyst.blueprint`, `/catalyst.assess`, `/catalyst.generate`), memory files with company reference material, company overlay skills, and an `adk-agents` domain skill.

She types `/specify`. The preset presents a structured template with ten sections — Business Context, Workflow Step by Step, Regulatory Requirements, Data Systems, External Partners, What We Own, Business Rules, Transformation Rules, Error Handling, and Acceptance Criteria. She fills it in using plain English, describing the step-by-step workflow ("first the customer calls, then the system classifies severity, then in parallel it enriches from three sources..."), the data systems involved, the external partner APIs, and her proprietary business logic as structured IF/THEN conditions. This takes about 20 minutes. The result is `spec.md` — a structured requirements document saved in her workspace.

She types `/plan` and answers a handful of technical questions — GCP region, LLM model, CI/CD tools, Terraform module source. This takes 5 minutes. The result is `plan.md`.

She types `/catalyst.blueprint`. This custom command connects to the **Blueprint Advisor MCP Server** — an LlmAgent running on Cloud Run, exposed as an MCP Server. Her coding agent calls `blueprint_start` via MCP protocol with her `spec.md` and `plan.md` as input. The call returns a task ID in under 2 seconds — the heavy work runs in the background. She doesn't need to know what happens inside the server — but here's what does:

The Blueprint Advisor reads her spec's natural language signals. "First the customer calls, then the system classifies severity" tells it Sequential. "In parallel it enriches from three sources" tells it Parallel. "Loop until quality score exceeds 0.85" tells it Loop. "Route high-severity to a human adjuster" tells it HITL. It searches the company's pattern catalog, skill catalog, and tool registry via Vertex AI Search (single-pass semantic retrieval), applies LLM reasoning guided by a company-curated system prompt, and assembles a recommendation. While this runs (15–60 seconds), her coding agent polls `blueprint_status` every 10 seconds and reports progress in the Chat pane: "Searching pattern catalog...", "Reasoning about architecture...", "Assembling blueprint...".

When the background pipeline completes, the coding agent calls `blueprint_result` and receives a JSON response containing the markdown content, base64-encoded diagram PNGs, and drawio XML files. It writes `app-blueprint.md` to the workspace along with component diagram PNGs, HA/DR diagram PNGs, and their editable drawio XML counterparts — all in the same feature directory. The markdown file is a structured document describing WHAT to build: 5 agents (Coordinator + Sequential + Parallel + Loop + HITL), 3 MCP servers (BigQuery, Cloud SQL, Vertex AI Search), 3 A2A agents (body shop, rental car, police report), 3 FunctionTool implementations (severity classifier, coverage calculator, notification sender — with her IF/THEN business rules included), infrastructure settings, EvalOps configuration, and a golden dataset derived from her acceptance criteria. Component diagrams are rendered as inline PNG images with editable drawio XML alongside. Sequence diagrams are inline mermaid code. NFRs, ADL, and tech stack are tables. Each recommendation is tagged with a confidence level (high/medium/low).

She reviews the markdown in her editor — the component diagram renders inline in VSCode's markdown preview, the sequence diagrams render as mermaid, and all tables are readable. The Blueprint Advisor assigned Cloud SQL to the wrong agent — she edits the table directly, changing `assigned_to: extract_details` to `assigned_to: fnol_coordinator`. She saves. Her coding agent calls `validate_composition` via MCP — a deterministic check that her edited pattern tree is valid (e.g., LoopAgent cannot nest inside ParallelAgent). It passes. Then `assemble_blueprint` finalizes the markdown. If she needs to edit the component diagram, she opens the drawio XML in draw.io, modifies it, and the updated diagram is assessed on her next `/catalyst.assess` run.

Before generating code, she runs the governance check. She types `/catalyst.assess`. The coding agent reads `app-blueprint.md` and extracts all 7 artifact types directly from it — the component diagram PNG from the `![...]()` reference in §4, HA/DR views from §13, sequence diagrams from the inline mermaid in §14, NFRs from the table in §10, architecture decisions log from §11, tech stack from §12, and patterns from §2 — packages them as a JSON document, and sends them to the **Governance Guardian MCP Server** using the same async pattern as the Blueprint Advisor (`assess_start` → poll `assess_status` → `assess_result`). While the EA assessment engine evaluates her solution (a black box to AgentCatalyst — the EA office owns all the assessment logic), she sees progress in the Chat pane: "Evaluating architecture compliance...", "Checking pattern adherence...", "Scoring HA/DR readiness...".

The assessment returns a scorecard and findings. One showstopper: her Aurora PostgreSQL has no cross-region DR strategy, violating ADR-205. Two non-critical findings: WAF rules not using the enterprise managed rule group, and Angular 17 not yet on the approved tech radar. She fixes the showstopper — adds Aurora Global Database with a us-west-2 read replica to her Terraform and updates the HA/DR view in her drawio. She runs `/catalyst.assess` again. This time: no showstoppers, score 88/100. The two remaining findings are flagged as acceptable tech debt.

She types `/catalyst.generate`. Before the 18-step generation pipeline runs, the coding agent makes one final call to the Governance Guardian — `recordTechDebt`. This tool checks whether any showstopper findings remain from her latest assessment. None do — the two remaining findings are classified as tech debt, recorded in the governance database (TD-2026-0142), and the Governance Guardian returns `{ signal: "resume" }`. The coding agent reports: "Governance gate passed. Tech debt recorded. Generating code..." and proceeds.

The coding agent reads the blueprint and generates all the code — but it doesn't guess HOW to write the code. It has **skills** installed that teach it the right way:

- **`adk-agents` skill** teaches it how to write correct ADK Python code — the right import paths, the right class constructors, the right way to wire tools to agents.
- **Company overlay skills** teach it which Terraform modules to use (with pinned versions), how to configure Dynatrace observability, how to generate Jenkins + Harness pipeline definitions (NOT deploy directly), and how to generate Model Armor callbacks.
- **`constitution.md`** encodes non-negotiable rules: never deploy directly, always use company Terraform modules, always generate pre-commit evaluation hooks. These are coding agent constraints, not meta-skills or decision frameworks.

The result: a complete project in her workspace — 6 agent class files, 3 MCP connections, 3 A2A clients, 3 FunctionTool files with first-draft business logic (the IF/THEN conditions from her spec are already implemented as working Python code), Model Armor callbacks, complete Terraform, Dynatrace config, Jenkins + Harness pipeline definitions, a pre-commit evaluation hook, Phoenix tracing config, a golden dataset derived from her acceptance criteria, and a 3-phase Harness evaluation pipeline. Every file follows company standards because the company overlay skills taught the coding agent those standards.

She opens `app/tools/severity_classifier.py` and reviews the first draft of generated business logic — the IF/THEN conditions she authored in the spec are already implemented as working Python code. This is her starting point, not a black box. She refines the logic, adds one edge case the spec didn't cover, and writes system prompts for each agent. Because she captured business rules in the spec, the manual work is only ~5–10% — primarily system prompts, eval dataset curation, and truly proprietary algorithms not expressible as structured IF/THEN rules.

She commits. The pre-commit hook runs — 5 evaluation sets execute in under 60 seconds via the Vertex AI Evaluation SDK. All metrics pass. She pushes and opens a PR. Her team reviews it — the generated code looks familiar because every AgentCatalyst project follows the same company patterns.

After the PR is merged, Jenkins runs Terraform to provision the infrastructure. Then Harness deploys the agent through the 3-phase evaluation pipeline: Phase A (Arize quality gates), Phase B (AutoSxS baseline comparison against the golden dataset), Phase C (2 edge cases routed to HITL triage where a reviewer approves them). After evaluation passes, Harness promotes through Non-Prod → Pre-Prod (canary at 10%) → Production (progressive rollout). If anything breaks, Harness rolls back automatically.

She never deployed from her laptop. She never provisioned a GCP resource manually. She never wrote a Dockerfile. All of that was either generated by the coding agent (Terraform, pipeline definitions, evaluation infrastructure) or handled by the company's CI/CD. The 80-95% was handled by the coding agent guided by skills. When business rules are authored in the spec, even FunctionTool bodies are generated as a first draft — the developer reviews and makes the code their own.

**Total time from "I need an FNOL agent" to generated code committed to GitHub: under 2 hours.** The remaining 2–4 hours are spent reviewing generated business logic, writing system prompts, curating eval datasets, and adding edge cases. Without AgentCatalyst, this entire process takes 7–8 weeks.

**Now imagine** a different developer on another team who needs to build a FastAPI microservice for order management. He installs the `agentcatalyst-microservice` preset instead. His `/specify` template has different sections — Service Purpose, API Contracts, Dependencies, Data Model. His Blueprint Advisor searches a different pattern catalog — microservice patterns instead of agent patterns. His coding agent loads a `fastapi` skill instead of an `adk-agents` skill. But the **company overlay skills are the same** — same Terraform modules, same Dynatrace config, same Jenkins/Harness pipelines, same security standards. The microservice follows the same company patterns as the agent. The platform team maintains one set of overlay skills, and every application type benefits.

### Brownfield: Adding an agent to an existing system

Not every agent starts from scratch. When adding an AI agent to an existing system with live APIs, production databases, and code you can't modify, the developer writes the spec differently. In the **External Integrations** section, she writes: "Loan origination REST API — WE operate this, EXISTING endpoints at /api/v2/applications. The agent MUST use these existing endpoints." In the **Internal Capabilities** section: "Credit score lookup — EXISTING internal function at /api/v2/credit-check."

The Blueprint Advisor reads phrases like "EXISTING REST API" and "MUST use these existing endpoints" and recommends FunctionTool wrappers around the existing REST endpoints — not new MCP connections or new services. The generated code wraps the existing API with thin Python functions. **The agent adapts to the existing system — never the other way around.** No existing database schemas, API contracts, or source code are modified.

**Architecture infographic:**

![AgentCatalyst Component Architecture](AgentCatalyst-GA-Architecture-Infographic.png)

---

## Technology Stack

| Component | Details |
|---|---|
| Agent Framework | Google ADK — Python |
| Runtime (API layer) | Cloud Run Service (GA) — hosts the MCP API layer for Blueprint Advisor |
| Runtime (Pipeline) | Cloud Run Jobs (GA) — runs the Blueprint Advisor LlmAgent pipeline (no timeout) |
| Task Store | AlloyDB (GA) — async task state for MCP Tasks lifecycle (24h TTL) |
| Task Queue | Cloud Tasks (GA) — enqueues pipeline jobs from `blueprint_start` |
| Spec Workflow | GitHub Spec Kit with AgentCatalyst preset (archetype-specific) |
| Blueprint Advisor | LlmAgent exposed as MCP Server. API layer on Cloud Run Service (async via MCP Tasks). Pipeline on Cloud Run Jobs. Task state in AlloyDB. Enqueue via Cloud Tasks. |
| Discovery | Vertex AI Search (archetype-specific catalogs: patterns, skills, tools) |
| IaC | Terraform + company TF modules via GitHub MCP Server |
| Security | Model Armor (standard), DLP, Secret Manager, SPIFFE, VPC-SC, CMEK |
| Gateway | Apigee Runtime Gateway (GA) |
| Observability | OTel → Dynatrace (APM) + Splunk (SIEM) + Arize Phoenix (traces) + Cloud Logging |
| Evaluation | Arize SaaS + Vertex AI Eval SDK + AutoSxS + HITL triage |
| CI/CD | Jenkins (infrastructure plane) + Harness (application plane + 3-phase EvalOps) |
| Source Control | GitHub + GitHub MCP Server for code commit |

---

## Five-Layer Architecture

```
Layer 1 — SPEC CAPTURE         /specify → spec.md, /plan → plan.md
Layer 2 — ARCHITECTURE ADVISORY Blueprint Advisor MCP Server → app-blueprint.md
Layer 3 — SKILL-GUIDED GEN     /catalyst.generate → complete project
Layer 4 — COMPANY CI/CD        Jenkins (infra) + Harness (deploy + EvalOps)
Layer 5 — RUNTIME & OPERATE    Cloud Run + Apigee + Dynatrace + Splunk
```

### Layer 1 — Spec Capture

> For step-by-step walkthroughs of spec writing (greenfield FNOL + brownfield microservice), see the Developer Guide, Sections 2-3. For spec writing tips, see Developer Guide, Section 4.

The developer installs the AgentCatalyst preset and runs `/specify` + `/plan`. The preset is archetype-specific — an agentic preset captures workflow ordering words and agent boundaries, a microservice preset captures API contracts and data models.

The spec template has 10 sections (6 original + 4 business logic sections added in v2):

| Section | Purpose | Impact on code generation |
|---|---|---|
| Business Problem | Context and value proposition | Informs Blueprint Advisor recommendations |
| Workflow | Step-by-step with ordering words | Blueprint Advisor maps to patterns |
| Data Sources | Data systems with workload types | Blueprint Advisor assigns MCP connections |
| External Integrations | Partner services | Blueprint Advisor assigns A2A or FunctionTool wrappers |
| Internal Capabilities | Proprietary logic | Blueprint Advisor flags as FunctionTool implementations |
| Infrastructure | GCP region, compliance, networking | Maps to Terraform and security config |
| **Business Rules** | Structured IF/THEN per decision point | Coding agent generates first-draft business logic |
| **Transformation Rules** | Field mappings and formulas | Coding agent generates data transformation functions |
| **Error Handling** | Timeout/retry per dependency | Coding agent generates try/catch with circuit breakers |
| **Acceptance Criteria** | GIVEN/WHEN/THEN assertions | Coding agent generates golden dataset + evalsets |

When business rules are in the spec, code generation reaches 90-95%. When omitted, 80% scaffolding with stubs.

### Layer 2 — Architecture Advisory (Blueprint Advisor MCP Server)

The Blueprint Advisor is an LlmAgent running on Cloud Run, **exposed as an MCP Server**. The coding agent connects via MCP protocol — this is the only universally compatible method (GitHub Copilot cannot make HTTP calls or run shell commands, but all major coding agents support MCP).

**Async invocation via MCP Tasks:** VS Code Copilot enforces a hard 10–15 second timeout on synchronous MCP tool calls. The Blueprint Advisor's internal pipeline (3 RAG queries + LLM reasoning + validation + assembly) takes 15–60 seconds depending on spec complexity. A synchronous call would be killed by Copilot before it completes. The Blueprint Advisor therefore uses the **MCP Tasks** async primitive (spec revision 2025-11-25): the coding agent starts a background task, polls for progress, and retrieves the result when complete. Each individual MCP call completes in under 2 seconds — well within any coding agent's timeout window.

**MCP Tools exposed to the coding agent:**

| MCP Tool | Type | Latency | Purpose |
|---|---|---|---|
| `blueprint_start(spec, plan)` | **ASYNC START** | < 2 seconds | Validates input, creates a background task in the Task Store, enqueues the pipeline via Cloud Tasks, returns `taskId` + `pollInterval` immediately |
| `blueprint_status(taskId)` | **POLL** | < 1 second | Returns current pipeline stage (searching / reasoning / validating / assembling) and a progress message for display to the developer |
| `blueprint_result(taskId)` | **RETRIEVE** | < 1 second | Returns JSON with: `markdown` (full app-blueprint.md content), `diagrams` (array of base64-encoded PNGs + drawio XMLs), `spec_hash`, `plan_hash`, `blueprint_hash`. The prompt file writes the .md and diagram files to the workspace. |
| `validate_composition(pattern_tree)` | **DETERMINISTIC** | < 1 second | Checks developer's edited pattern selections against adjacency matrix. Returns valid/invalid + reason. Called after developer edits the blueprint |
| `assemble_blueprint(selections, spec, plan)` | **DETERMINISTIC** | < 1 second | Rebuilds final markdown from validated selections. Template-filling + diagram rendering (graphviz → PNG + drawio), no LLM involved. Called after validation passes |

The first three tools implement the async MCP Tasks pattern. The last two are called after the developer has reviewed and edited the blueprint — they remain synchronous because they are fast and deterministic.

**Task lifecycle:**

| Status | Meaning |
|---|---|
| `accepted` | Task record created, queued for execution |
| `working` | Pipeline executing (substage: searching / reasoning / validating / assembling) |
| `completed` | Blueprint + confidence scores available for retrieval |
| `failed` | Structured error (LlmAgent failure, RAG timeout, composition invalid) |

Task records are stored in AlloyDB with a 24-hour TTL. This allows the developer to retrieve a result even after closing and reopening VSCode.

**Blueprint Advisor versioning:**

Every markdown blueprint includes version metadata in its header:

```yaml
# Generated by: blueprint-advisor/v2.3.1
# System prompt: v1.8 (SHA: abc123)
# Pattern catalog: 2026-05-10 (11 patterns)
# Timestamp: 2026-05-10T14:30:00Z
```

This enables reproducibility: if a developer needs to understand why a recommendation was made, the platform team can re-invoke the same Blueprint Advisor version with the same spec. The Operations Runbook (Section 9) covers the deployment procedure for new versions, including maintaining 2 versions in production for rollback.

**Internal to the MCP Server (NOT exposed to the coding agent):**

| Internal Component | Purpose |
|---|---|
| Blueprint Advisor LlmAgent | RAG + LLM reasoning guided by company system prompt |
| `search_patterns()` | RAG tool — queries Pattern Catalog in Vertex AI Search |
| `search_skills()` | RAG tool — queries Skill Catalog in Vertex AI Search |
| `search_tools()` | RAG tool — queries Tool Registry in Vertex AI Search |
| Company system prompt | Curated best practices, constraints, preferences |
| Vertex AI Search connections | 3 archetype-specific data stores |

**MCP protocol version:** The Blueprint Advisor MCP Server implements **MCP protocol version 2025-11-25** (which introduced the Tasks primitive for async operations). Coding agent compatibility:

| Coding Agent | MCP Version Supported | Tasks Support | Status |
|---|---|---|---|
| GitHub Copilot | 2025-11-25 | ✅ via prompt-file polling | ✅ Tested |
| Claude Code | 2025-11-25 | ✅ native | ✅ Tested |
| Cursor | 2025-11-25 | ✅ via prompt-file polling | ✅ Tested |
| Gemini CLI | 2025-11-25 | ✅ via prompt-file polling | ⚠️ Community-tested |
| Windsurf | 2025-11-25 | ✅ via prompt-file polling | ⚠️ Community-tested |

For coding agents without native MCP Tasks support (most IDE-based agents), the `/catalyst.blueprint` prompt file drives the start → poll → result loop. The LLM naturally handles the polling — each tool call is a fast round-trip.

The coding agent calls `blueprint_start` ONCE (which kicks off the background pipeline), then polls `blueprint_status` until complete, then retrieves the result. The coding agent has no direct access to Vertex AI Search, no access to the company system prompt, and no ability to invoke the LlmAgent directly. All intelligence lives on the server side.

**`/catalyst.blueprint` command flow (async via MCP Tasks):**

1. Coding agent calls `blueprint_start(spec, plan)` via MCP → returns `taskId` in < 2 seconds
2. Background pipeline starts on Cloud Run Jobs (no timeout constraint):
   - Runs Blueprint Advisor LlmAgent internally (RAG search → LLM reasoning → recommendations)
   - Validates composition against adjacency matrix
   - Assembles blueprint from validated selections
   - Stores result in AlloyDB Task Store
3. Coding agent polls `blueprint_status(taskId)` every 10 seconds via MCP (< 1 second each)
   - Reports progress to developer in Chat pane: "Searching pattern catalog...", "Reasoning about architecture...", etc.
4. When status returns `completed`, coding agent calls `blueprint_result(taskId)` via MCP
5. Recommendations with confidence scores returned in < 1 second
6. Coding agent saves them as `app-blueprint.md`
7. Developer reviews in markdown editor, edits selections
8. Coding agent calls `validate_composition(edited_pattern_tree)` — deterministic pass/fail (< 1 second)
9. Coding agent calls `assemble_blueprint(validated_selections, spec, plan)` — deterministic blueprint assembly (< 1 second)
10. Result: final `app-blueprint.md` written to workspace

**Prompt-file orchestration:** The `/catalyst.blueprint` prompt file drives the start → poll → result loop without custom client code. The LLM naturally handles the polling — each tool call is a fast round-trip within any coding agent's timeout window. The developer sees progress messages in the Chat pane throughout.

**Offline / disconnected fallback:**

If the Blueprint Advisor MCP Server is unreachable (VPN down, server maintenance, network issue), the developer is NOT blocked. Two fallback paths exist:

1. **Manual YAML authoring:** The developer writes `app-blueprint.md` manually using the schema reference (see Appendix A.10 for a complete example). The coding agent can still run `/catalyst.generate` against a hand-written blueprint — it only needs `app-blueprint.md`, not the MCP Server.

2. **Cached recommendation:** If the developer previously received a recommendation for a similar spec, they can copy and modify that YAML. The `validate_composition` and `assemble_blueprint` MCP tools are lightweight, synchronous, and may still be available even when the background pipeline is down (they don't depend on Vertex AI Search or LLM reasoning).

3. **Stale task retrieval:** If a `blueprint_start` succeeded but the developer lost connectivity before calling `blueprint_result`, the result remains in the Task Store for 24 hours. Reconnecting and calling `blueprint_result(taskId)` retrieves the completed blueprint.

The Developer Guide (Section 5) includes the complete schema and an annotated example that developers can use as a starting template for manual authoring

**The 11 agentic patterns (Phase 1 catalog):**

| Pattern | ADK Class | When Blueprint Advisor selects it |
|---|---|---|
| Coordinator | LlmAgent | Root orchestrator — spec describes multiple specialized sub-agents |
| Sequential Pipeline | SequentialAgent | "First... then... finally" ordering |
| Parallel Fan-out | ParallelAgent | "Simultaneously" or "in parallel" |
| Loop / Iterative Refinement | LoopAgent | "Repeat until" or "refine until threshold" |
| Human-in-the-Loop | LlmAgent + callback | "Route to human" or "requires approval" |
| RAG / Retrieval-Augmented | LlmAgent + Vertex AI Search | "Search documents" or "knowledge base" |
| ReAct (Reason + Act) | LlmAgent + tools | Complex reasoning with tool use |
| Event-Driven | LlmAgent + Pub/Sub | "When event occurs" or "triggered by" |
| Supervisor | LlmAgent + delegation | "Oversee" or "quality check" |
| Critic / Evaluator | LlmAgent | "Validate" or "score quality" |
| Custom Tool Agent | LlmAgent + FunctionTool | Proprietary logic — domain-specific |

### Blueprint Advisor MCP Server — Security

The Blueprint Advisor MCP Server receives spec.md content that may contain proprietary business rules, competitive intelligence, partner names, and regulatory details. The following security controls are required:

**Authentication — OAuth 2.1 with Entra ID:**

Both the Blueprint Advisor and Governance Guardian MCP Servers require OAuth 2.1 authentication via the company's **Microsoft Entra ID** (formerly Azure AD) identity provider. The coding agent authenticates the developer once, then attaches the access token to every MCP tool call. The token is validated by both MCP Servers — a developer authenticated for the Blueprint Advisor does NOT need to re-authenticate for the Governance Guardian (same token, same IdP, same audience scope).

The following sequence diagram shows the complete authentication flow from the developer's first `/catalyst.blueprint` command through token acquisition to authenticated MCP tool calls on both servers:

```mermaid
sequenceDiagram
    autonumber
    participant Dev as Developer<br>(VSCode)
    participant CA as Coding Agent<br>(Copilot / Claude Code)
    participant Entra as Microsoft Entra ID<br>(OAuth 2.1 Authorization Server)
    participant BA as Blueprint Advisor<br>MCP Server
    participant GG as Governance Guardian<br>MCP Server
    participant TS as Task Store<br>(AlloyDB)

    Note over Dev,Entra: Phase 1 — First-time authentication (one-time browser flow)

    Dev->>CA: /catalyst.blueprint
    CA->>CA: Read MCP endpoint config from preset.yml<br>(client_id, token_endpoint, scopes)
    CA->>CA: Check token cache — no valid token found

    CA->>Dev: Opens browser for company SSO login
    Dev->>Entra: Browser redirect to /authorize<br>response_type=code, client_id, scope=agentcatalyst.mcp<br>code_challenge (PKCE S256)
    Entra->>Dev: Company SSO login page (Entra ID)
    Dev->>Entra: Enter credentials + MFA
    Entra->>CA: Authorization code (via redirect URI)

    CA->>Entra: POST /token<br>grant_type=authorization_code<br>code + code_verifier (PKCE)
    Entra-->>CA: access_token (JWT, 1hr) + refresh_token

    CA->>CA: Cache tokens locally<br>(secure OS keychain)

    Note over CA,BA: Phase 2 — Authenticated MCP tool calls (Blueprint Advisor)

    CA->>BA: blueprint_start(spec, plan)<br>Authorization: Bearer {access_token}
    BA->>BA: Validate JWT signature (Entra ID JWKS endpoint)<br>Verify audience = agentcatalyst.mcp<br>Extract user identity (sub claim = sarah@company.com)
    BA->>TS: INSERT task (owner_id = sarah@company.com)
    BA-->>CA: { taskId, pollInterval }

    loop Polling (each call carries same token)
        CA->>BA: blueprint_status(taskId)<br>Authorization: Bearer {access_token}
        BA->>BA: Validate JWT (cached JWKS, ~1ms)
        BA-->>CA: { status, stage, message }
    end

    CA->>BA: blueprint_result(taskId)<br>Authorization: Bearer {access_token}
    BA->>TS: SELECT result WHERE owner_id = sarah@company.com
    BA-->>CA: { markdown, diagrams, hashes }

    Note over CA,GG: Phase 3 — Same token, different MCP Server (Governance Guardian)

    Dev->>CA: /catalyst.assess
    CA->>CA: Token still valid (< 1 hour old)

    CA->>GG: assess_start(solution_package)<br>Authorization: Bearer {access_token}
    GG->>GG: Validate same JWT (same Entra ID JWKS)<br>Same audience scope, same user identity
    GG->>TS: INSERT task (owner_id = sarah@company.com)
    GG-->>CA: { taskId, pollInterval }

    Note over CA,GG: Polling + result use same token pattern

    Note over CA,Entra: Phase 4 — Silent token refresh (automatic, no user interaction)

    CA->>CA: Token expires in 5 minutes
    CA->>Entra: POST /token<br>grant_type=refresh_token<br>refresh_token={cached}
    Entra-->>CA: New access_token (1hr) + new refresh_token
    CA->>CA: Update token cache

    CA->>BA: Next MCP call uses new token seamlessly
```

**Key authentication design decisions:**

| Decision | Rationale |
|---|---|
| **OAuth 2.1** (not 2.0) | OAuth 2.1 mandates PKCE for all clients and prohibits the implicit grant — both required for a desktop IDE context where a client secret cannot be securely stored |
| **Entra ID as IdP** | Company standard. All developers have Entra ID accounts via company SSO. No separate credentials to manage. |
| **Single audience scope** (`agentcatalyst.mcp`) | Both Blueprint Advisor and Governance Guardian share the same scope — one token works for both servers. The developer authenticates once. |
| **PKCE (S256)** | Required by OAuth 2.1 for public clients (the IDE cannot securely store a client secret). The code_verifier/code_challenge exchange prevents authorization code interception. |
| **JWT validation at each MCP Server** | Each server independently validates the JWT signature against Entra ID's JWKS endpoint (cached, ~1ms). No shared session state between servers. |
| **1-hour token with silent refresh** | Developer authenticates once per day (or when the refresh token expires, typically 24 hours). All subsequent calls use silent refresh — no browser popup. |
| **`owner_id` from JWT `sub` claim** | The Task Store's tenant isolation uses the `sub` claim (e.g., `sarah@company.com`) from the validated JWT as the `owner_id`. This is set at `blueprint_start` / `assess_start` time and enforced on every subsequent status/result call. |
| **Token cached in OS keychain** | The coding agent stores tokens in the OS-native secure store (macOS Keychain, Windows Credential Manager, Linux Secret Service). NOT in plain text, NOT in the workspace. |

**Credential provisioning (zero manual config):**
- The MCP endpoint URL, OAuth client ID, Entra ID token endpoint, and required scopes are configured in the preset's `preset.yml` under an `mcp_servers` section
- When the developer installs the preset (`specify preset add agentcatalyst-enterprise`), the connection configuration is installed automatically
- First-time `/catalyst.blueprint` or `/catalyst.assess` triggers the browser-based SSO flow
- Subsequent commands use the cached token with silent refresh

**Transport security:**
- All MCP protocol connections use **TLS 1.3** minimum (enforced by Cloud Run's default TLS termination)
- The MCP endpoint  resolves to an HTTPS endpoint with a valid certificate
- Mutual TLS (mTLS) is optional — recommended for environments requiring client certificate authentication

**Spec content handling:**
- spec.md and plan.md content is transmitted via `blueprint_start` and processed **in-memory** during the background pipeline run
- Spec content is stored in the AlloyDB Task Store only as part of the task record during processing (encrypted at rest, 24-hour TTL, then auto-deleted)
- Spec content is **NOT persisted** beyond the task TTL
- Telemetry captures the spec hash (SHA-256) for traceability, NOT the spec content itself
- Spec content does not leave the configured GCP region (Cloud Run regional deployment; AlloyDB co-located)

**Task Store tenant isolation:**
- Every task record in AlloyDB carries an `owner_id` field set to the authenticated user's identity from the OAuth token at `blueprint_start` time
- `blueprint_status` and `blueprint_result` enforce `owner_id == caller_id` before returning data — a developer cannot read another developer's task
- `taskId` is a **cryptographically random UUID** (128-bit, `uuid4`), not sequential — preventing enumeration attacks
- AlloyDB PostgreSQL Row-Level Security (RLS) policies enforce the `owner_id` check at the database layer as defense-in-depth (not just application-layer validation)

**Cloud Tasks queue security:**
- The API layer service account requires `cloudtasks.tasks.create` on the blueprint-tasks queue
- The pipeline job service account requires `cloudtasks.tasks.lease` (pull model) or is invoked directly by Cloud Tasks (push model)
- The Cloud Tasks queue is configured with a dead-letter topic (`blueprint-tasks-dlq`) for tasks that fail after max retries
- Queue IAM is scoped to the Blueprint Advisor service accounts only — no developer-facing access

> See the Operations Runbook, Section 9 for MCP Server operational security (health checks, deployment procedures, scaling, Task Store maintenance).

### Blueprint Advisor MCP Server — Capacity and Rate Limiting

The Blueprint Advisor uses an async two-component architecture: a lightweight **MCP API layer** (Cloud Run Service) handles the three fast tools, and a **background pipeline** (Cloud Run Jobs) runs the LlmAgent work with no timeout constraint. Each `blueprint_start` triggers a pipeline run that takes 15–60 seconds (3 RAG queries + LLM reasoning + validation + assembly) and costs ~$0.01 (Vertex AI Search + Gemini API tokens).

**Rate limits (enforced at the MCP API layer on `blueprint_start` only):**

| Limit | Value | Rationale |
|---|---|---|
| Per-developer | 10 starts/hour | Developers rarely need more than 3-5 iterations per use case |
| Per-team | 30 starts/hour | Prevents one team from monopolizing the pipeline |
| Concurrent pipelines | 10 simultaneous | Cloud Run Jobs max-concurrent setting |
| `blueprint_status` / `blueprint_result` | No limit | Lightweight AlloyDB queries, negligible cost |
| `validate_composition` / `assemble_blueprint` | No limit | Deterministic, sub-second, negligible cost |

When a rate limit is hit, `blueprint_start` returns a clear error: "Rate limit exceeded. You have used N/10 starts this hour. Next start available in M minutes."

**Capacity planning:**

| Metric | Expected (Year 1) | Infrastructure |
|---|---|---|
| Daily active developers | 10–20 | API layer: `--min-instances 1` (avoid cold starts) |
| Peak concurrent pipelines | 3–5 | Cloud Run Jobs: max-concurrent 10 (headroom) |
| Monthly `blueprint_start` calls | 200–500 | ~$2–5/month Vertex AI Search + $5–10/month Gemini |
| Monthly API layer compute | ~5 Cloud Run instance-hours | ~$2–5/month |
| Monthly pipeline compute | ~15 Cloud Run Job-hours | ~$5–10/month |
| Task Store (AlloyDB) | ~500 task records/month × 24h TTL | ~$1/month |

**Total monthly Blueprint Advisor cost at expected usage: $15–30/month.** The exec summary's $500–1,500/month GCP infrastructure estimate covers the full platform, not just the Blueprint Advisor. The reconciliation:

| Component | Monthly cost (Year 1) |
|---|---|
| Blueprint Advisor (API layer + pipeline + AlloyDB + Gemini + Vertex AI Search) | $15–30 |
| Governance Guardian (API layer + AlloyDB tables + Cloud Tasks queue) | $10–25 |
| Cloud Tasks queues (blueprint-tasks + governance-assess) | <$2 |
| Arize Phoenix SaaS (tracing for deployed agents) | $200–400 |
| Dynatrace APM (platform + deployed agents) | $100–300 |
| Cloud Run for deployed agents (runtime, not Blueprint Advisor) | $100–400 |
| Vertex AI Search (larger catalogs at scale) | $50–100 |
| Cloud Logging + Splunk ingestion | $50–150 |
| Model Armor + DLP | $25–75 |
| **Total GCP platform infrastructure** | **$540–1,455** |

The $500–1,500/month estimate in the exec summary is accurate for the full platform. The capacity section above covers only the Blueprint Advisor's share.

> See Operations Runbook, Section 9 for Cloud Run scaling configuration and adjustment triggers.

### Layer 3 — Skill-Guided Code Generation

> For the complete code generation walkthrough with generated directory trees, see Developer Guide, Section 2 (greenfield) and Section 3 (brownfield). For writing tests for generated code, see Developer Guide, Section 7.

The coding agent reads the markdown blueprint and generates the complete project. It is constrained by three layers:

| Layer | Source | Role |
|---|---|---|
| **Blueprint** (WHAT) | `app-blueprint.md` from Blueprint Advisor | Defines topology, tool assignments, infrastructure config |
| **Archetype skill** (HOW) | e.g., `adk-agents` SKILL.md | Teaches correct framework-specific patterns, imports, constructors |
| **Overlay skills** (MUST) | Company overlay SKILL.md files | Teaches non-negotiable company standards (Terraform, Dynatrace, CI/CD, security) |
| **Constitution.md** | In the preset | Non-negotiable rules the coding agent MUST follow (e.g., never deploy directly) |

**Important: Constitution.md contains coding agent rules — NOT meta-skills or decision frameworks.** The 4 meta-skills (pattern-composition, data-platform-selection, agent-boundary, skill-tool-discovery) exist only in AgentForge and are loaded into the Design Agent via ADK SkillToolset. AgentCatalyst's constitution.md is a different file with a different purpose: it constrains the coding agent during code generation.

**What code generation produces (80-95% depending on business rules in spec):**

| Generated component | Source (blueprint section) |
|---|---|
| ADK agent class hierarchy | `agents:` |
| MCP server connections | `tools.mcp_servers:` |
| A2A client connections | `tools.a2a_agents:` |
| FunctionTool implementations (first draft from business rules) | `tools.function_tools:` + `business_rules:` |
| Terraform modules | `infrastructure:` |
| Dynatrace observability config | `observability:` |
| Jenkins + Harness pipeline definitions | `ci_cd:` |
| Model Armor callbacks | `security:` |
| Pre-commit evaluation hook | `evalops:` |
| Arize Phoenix tracing config | `evalops:` |
| Golden dataset (starter from acceptance criteria) | `golden_dataset:` |
| 3-phase Harness evaluation pipeline | `evalops:` |

#### IaC generation — how the Terraform overlay skill uses GitHub URLs

The Terraform generation flow is the most infrastructure-critical step in the pipeline. The coding agent **never writes raw Terraform resources** (`google_cloud_run_v2_service`, `aws_rds_instance`, etc.) — it always references **company modules** from the GitHub URLs in `app-blueprint.md` §8. This ensures every resource is tagged, compliant, DR-aware, and version-pinned.

**Two types of GitHub URLs in §8:**

| Type | Example | Purpose |
|---|---|---|
| **Pattern repo** | `github.com/company/tf-agentic-pilot-cold` | Complete IaC scaffold for an entire architectural pattern + DR strategy combination. Wires together multiple service modules. |
| **Service module** | `github.com/company/tf-cloud-sql` | Individual Terraform module for one cloud service. Enforces company standards (naming, tagging, encryption, HA). |

The pattern repo is selected by the Blueprint Advisor based on two fields: the archetype (agentic, microservice, pipeline, API) and the DR strategy from plan.md (backup-restore, pilot-cold, pilot-ondemand, warm-standby). The service modules are selected based on the tech stack in §12.

**Step-by-step generation flow:**

1. **Read §8** — The IaC overlay skill (`company-terraform` SKILL.md) reads the Infrastructure Modules table from `app-blueprint.md` and builds a dependency graph: which pattern repo to scaffold from, and which service modules to compose.

2. **Read module interfaces via GitHub MCP Server** — For each GitHub URL, the coding agent calls the GitHub MCP Server (`read_file` tool) to read three files: `variables.tf` (what parameters the module needs), `outputs.tf` (what it exports for wiring), and `examples/{archetype}/terraform.tfvars` (reference values for this use case type). The coding agent does NOT clone repos — it reads files through MCP, respecting the developer's GitHub authentication and access controls.

3. **Map blueprint fields to module variables** — The skill contains a deterministic mapping table (no LLM guessing) that maps blueprint sections to Terraform variables:

   | Blueprint source | Terraform variable | Example value |
   |---|---|---|
   | §1 Metadata: `solution_id` | `project_name` | `fnol-claims-agent` |
   | §1 Metadata: `region_primary` | `primary_region` | `us-east1` |
   | §1 Metadata: `region_dr` | `dr_region` | `us-west1` |
   | §1 Metadata: `dr_strategy` | Pattern repo selection | `pilot-cold` → `tf-agentic-pilot-cold` |
   | §3 Agent Topology: agent names | `services{}` map | One Cloud Run service per agent with CPU/memory |
   | §5 Tool Bindings: MCP endpoints | `mcp_server_endpoints{}` | Connection strings per tool |
   | §7 MCP Server Configs: auth methods | `auth_configs{}` | mTLS / OAuth / API Key per server |
   | §10 NFRs: availability target | HA configuration | 99.95% → `ha_enabled = true` |
   | §10 NFRs: RPO | Cross-region replica | RPO < 1 hour → `replica_region = var.dr_region` |
   | §12 Tech Stack: data layer | Service module selection | Cloud SQL → `tf-cloud-sql` |

4. **Generate the Terraform project** — The skill generates a complete directory structure:

   ```
   terraform/
   ├── main.tf             ← Root module: composes pattern repo + service modules
   ├── variables.tf        ← All variables with descriptions
   ├── terraform.tfvars    ← Pre-filled values from blueprint
   ├── outputs.tf          ← Exported values for CI/CD pipeline
   ├── versions.tf         ← Provider versions (pinned from module repos)
   ├── backend.tf          ← GCS/S3 backend for state
   ├── environments/
   │   ├── dev.tfvars
   │   ├── staging.tfvars
   │   └── prod.tfvars     ← Multi-region values for production
   └── dr/
       ├── failover.tf     ← Failover triggers and health checks
       ├── failback.tf     ← Failback procedure resources
       └── lifecycle.tf    ← All 4 lifecycle scenarios from blueprint §13
   ```

5. **Wire modules together** — The root `main.tf` references each company module via its GitHub URL with a pinned version (`?ref=v2.3.0`), passes in variables resolved from the blueprint, and wires module outputs to inputs (e.g., Cloud SQL connection string → agent environment variable). Example:

   ```hcl
   module "claims_db" {
     source  = "github.com/company/tf-cloud-sql?ref=v3.1.0"
     instance_name  = "${var.project_name}-claims-db"
     region         = var.primary_region
     ha_enabled     = true              # From §10 NFRs: 99.95% availability
     replica_region = var.dr_region     # From §10 NFRs: RPO < 1 hour
   }
   ```

**Critical skill rule:** The `company-terraform` SKILL.md contains: *"NEVER use raw `google_*` or `aws_*` Terraform resources. ALWAYS reference a company module from app-blueprint.md §8. If no module exists for a required service, add `# TODO: Request tf-{service} module from platform team` and skip the resource."* This ensures the coding agent cannot generate non-compliant infrastructure even if it "knows" the raw Terraform syntax.

**GitHub MCP Server role in the flow:** The architecture diagram shows a dashed arrow from Step 4 (code generation) to the GitHub MCP Server. This represents the coding agent reading module repos during generation — it's the only step where the coding agent accesses GitHub directly. The Blueprint Advisor accessed GitHub earlier (Step 2) to discover which repos exist; the coding agent accesses the same repos (Step 4) to read the actual module interfaces and generate compliant Terraform.

**OPA policy validation (Plan Gate):** The generated Terraform is validated by OPA policies at the Plan Gate before the CI/CD pipeline provisions infrastructure (see Layer 4). OPA checks include: no public IPs, CMEK encryption on all data stores, VPC-SC perimeter membership, DR strategy matches plan.md, and all modules are from approved company repos. If OPA validation fails, the developer must fix the Terraform before the pipeline proceeds.

**What the developer implements (5-20%):**

| Task | Why it can't be generated | Priority |
|---|---|---|
| Review FunctionTool business logic | First draft generated from spec rules — developer refines and makes it their own | P0 |
| System prompts per agent | Requires domain expertise, tone, persona | P0 |
| Eval dataset curation | Requires real-world edge cases beyond acceptance criteria | P1 |
| Proprietary algorithms | ML models, actuarial formulas not expressible as IF/THEN | P1 |
| Pydantic output schemas | Domain-specific data contracts | P2 |

### Layer 4 — Company CI/CD (outside AgentCatalyst scope)

AgentCatalyst generates code and pipeline definitions. The company's existing CI/CD executes them.

| Pipeline | Tool | Purpose |
|---|---|---|
| Infrastructure plane | Jenkins | `terraform plan` → `terraform apply` → provisions Cloud Run, Apigee, Cloud SQL, Model Armor, VPC-SC |
| Application plane | Harness | Deploys agent → runs 3-phase EvalOps → promotes Non-Prod → Pre-Prod (canary) → Production |

**EvalOps — three-layer evaluation lifecycle:**

| Layer | What it does | When it runs |
|---|---|---|
| **Layer 1: Inner Loop** | Pre-commit hook runs 5-10 evalsets in <60 seconds via Vertex AI Eval SDK. Blocks commit if metrics regress >10%. | Developer's laptop, before `git commit` |
| **Layer 2: Deep Dive** | ADK tracing + Arize Phoenix captures LLM calls, tool calls, agent delegation. Explains WHY agents fail. | Local dev (`localhost:6006`) + deployed (OTel → Dynatrace) |
| **Layer 3: Outer Loop** | 3-phase Harness pipeline: Phase A (Arize quality gates), Phase B (AutoSxS baseline comparison), Phase C (HITL triage for flagged cases) | CI/CD pipeline, after PR merge |

**Phoenix tracing scope:** Phoenix tracing is for **generated agents at runtime** — LLM calls, tool calls, and agent delegation within your deployed agent. The Blueprint Advisor background pipeline is **not** traced by Phoenix; it is traced via Cloud Logging (structured logs per pipeline stage) and Dynatrace APM (OTel spans for RAG query latency, LLM reasoning time, and end-to-end pipeline duration). Platform engineers troubleshooting Blueprint Advisor performance use Dynatrace, not Phoenix. See the Operations Runbook, Section 9 for monitoring details.

**Golden dataset quality gate (enforced by pre-commit hook):**

The pre-commit hook validates the golden dataset before allowing a commit:

| Check | Minimum | What it catches |
|---|---|---|
| Total entries | ≥ 10 per agent | Low-coverage datasets that make evaluation meaningless |
| Edge cases | ≥ 3 | Datasets that only test the happy path |
| Negative tests | ≥ 1 (expected failure) | Datasets that don't verify error handling |
| All agents covered | 100% of agents in blueprint | Agents with zero evaluation coverage |

If the golden dataset fails any check, the pre-commit hook blocks with: "Golden dataset quality gate failed: [reason]. Add more entries before committing. See Developer Guide, Section 4b for guidance."

> For operational procedures for EvalOps maintenance (pre-commit hook tuning, Phoenix retention, Harness threshold updates, meta-evaluation procedure), see the Operations Runbook, Section 8.

**Golden Dataset lifecycle:** Acceptance criteria in spec → starter golden dataset → developer curation during testing → production feedback (Arize drift detection → failure sampling → human annotation → golden dataset update) → quarterly meta-evaluation (audit automated judges, ≥85% agreement threshold).

### Layer 5 — Runtime & Operate

All runtime services are GA with SLA backing:

| Component | Service | Purpose |
|---|---|---|
| Agent runtime | Cloud Run | Container-based agent hosting, scale-to-zero |
| API Gateway | Apigee Runtime Gateway | OAuth 2.1/OIDC, mTLS, rate limiting, API Products |
| Observability | Dynatrace + Splunk + OTel Collector | APM, SIEM, distributed tracing |
| Content screening | Model Armor (standard) | Google's default single-pass screening. Segmented Model Armor (per-source attribution with source-specific remediation) is a future roadmap item — it requires custom implementation beyond the Model Armor API. Standard Model Armor provides adequate content screening for GA. |
| Security | VPC-SC + CMEK + Secret Manager + Workload Identity | Data protection, key management, identity |

---

## app-blueprint.md — Template and Delivery

→ *Developer Guide §5 contains the full FNOL reference example with all 18 sections populated.*

### Why markdown over YAML

The previous `app-blueprint.yaml` was a machine-readable data file. The new `app-blueprint.md` is a **structured markdown document** that serves three roles simultaneously: (1) human-readable review artifact that renders natively in GitHub and VSCode with inline diagrams, (2) single input to Governance Guardian (`/catalyst.assess` extracts all 7 artifact types from one file), and (3) machine-readable input to code generation (`/catalyst.generate` parses sections deterministically).

### Workspace file layout

When `blueprint_result` delivers the blueprint, the coding agent writes:

```
features/fnol-claims-agent/
├── app-blueprint.md                    ← The blueprint (structured markdown, 18 sections)
├── fnol-component-diagram.png          ← Component diagram (rendered PNG, inline in markdown)
├── fnol-component-diagram.drawio.xml   ← Component diagram (editable in draw.io)
├── fnol-hadr-diagram.png               ← HA/DR lifecycle diagram (rendered PNG, inline in markdown)
├── fnol-hadr-diagram.drawio.xml        ← HA/DR diagram (editable in draw.io)
├── spec.md                             ← (already in workspace)
└── plan.md                             ← (already in workspace)
```

The `.md` file references PNGs with relative paths (`![Component Diagram](fnol-component-diagram.png)`) so they render inline in VSCode markdown preview and GitHub. The `.drawio.xml` files allow the SA to edit diagrams in draw.io — updated diagrams are picked up automatically on the next `/catalyst.assess` run.

### How `blueprint_result` delivers binary files

The MCP tool returns a JSON response with three fields:

```json
{
  "markdown": "<full content of app-blueprint.md>",
  "diagrams": [
    { "filename": "fnol-component-diagram.png", "format": "png", "content_base64": "..." },
    { "filename": "fnol-component-diagram.drawio.xml", "format": "drawio", "content_base64": "..." },
    { "filename": "fnol-hadr-diagram.png", "format": "png", "content_base64": "..." },
    { "filename": "fnol-hadr-diagram.drawio.xml", "format": "drawio", "content_base64": "..." }
  ],
  "spec_hash": "sha256:...", "plan_hash": "sha256:...", "blueprint_hash": "sha256:..."
}
```

The `/catalyst.blueprint` prompt file instructs the coding agent to write `app-blueprint.md` from the `markdown` field, and base64-decode each `diagrams` entry to the same directory.

> The `blueprint_result` MCP call is authenticated via OAuth 2.1 (see Layer 2 Security above) — the blueprint content is protected by Entra ID authentication and TLS 1.3 transport encryption.

### Diagram generation (inside the pipeline)

- **Component diagram (PNG + drawio):** Stage 4 (`assemble_blueprint`) assembles a graphviz DOT description from the agent topology, MCP connections, A2A boundaries, and infrastructure components. Renders to PNG via graphviz. Converts to drawio XML via DOT-to-drawio transform.
- **HA/DR diagram (PNG + drawio):** Stage 4 reads the DR strategy from plan.md and generates lifecycle views (Initial Provisioning → Component Failure / HA → DR Failover → DR Failback). Rendered to PNG and drawio.
- **Sequence diagrams (mermaid):** Generated as mermaid `sequenceDiagram` code and embedded inline in the markdown (§14). No separate file — mermaid renders natively in GitHub and VSCode.

### The 18 sections

| # | Section | Format | Consumers |
|---|---|---|---|
| 1 | Metadata | Key-value table | All |
| 2 | Pattern Composition | Table + validation notes | Code gen, Governance |
| 3 | Agent Topology | Table | Code gen, Governance |
| 4 | Component Diagrams | Inline PNG + drawio ref | SA review, Governance |
| 5 | Tool Bindings | Table | Code gen, Governance |
| 6 | Skill References | Table | Code gen |
| 7 | MCP Server Configs | Table | Code gen |
| 8 | Infrastructure Modules | Table | Code gen, Governance |
| 9 | Business Rules | Structured IF/THEN per FunctionTool | Code gen |
| 10 | NFRs | Table | Governance |
| 11 | Architecture Decisions Log | Table | Governance |
| 12 | Tech Stack | Table | Governance |
| 13 | HA/DR Views | Inline PNG + drawio ref + lifecycle table | SA review, Governance |
| 14 | Sequence Diagrams | Inline mermaid code | SA review, Governance |
| 15 | Evaluation Config | Table | Code gen |
| 16 | Screening Config | Table | Code gen |
| 17 | Pipeline Configs | Table | Code gen |
| 18 | Confidence Scores | Table | SA review |

### Governance Guardian extraction (simplified)

Because all artifacts are assembled in `app-blueprint.md`, the `/catalyst.assess` prompt file reads one file instead of searching the workspace:

| Artifact | Extracted from |
|---|---|
| TSA component diagram | §4 PNG reference |
| HA/DR views | §13 PNG reference + lifecycle table |
| Sequence diagrams | §14 inline mermaid |
| NFRs | §10 table |
| Architecture Decisions Log | §11 table |
| Tech stack | §12 table |
| Patterns used | §2 table |

---

## Governance Model

### Who owns what

| Component | Owner | Responsibilities |
|---|---|---|
| AgentCatalyst platform | Platform Engineering | Blueprint Advisor MCP Server, Governance Guardian MCP Server, overlay skills, preset catalog, Vertex AI Search data stores |
| Pattern catalog | Enterprise Architecture | Pattern documentation, composition rules, HA/DR views |
| **EA governance standards** | **Enterprise Architecture** | **Governance Guardian assessment logic, scoring rubrics, EA standards (black box to AgentCatalyst)** |
| **Tech Debt Registry** | **Enterprise Architecture + LOB teams** | **Accepted tech debt tracking, resolution follow-up** |
| Individual use cases | LOB development teams | Spec writing, blueprint review, governance assessment review, FunctionTool refinement, system prompts |
| CI/CD pipelines | DevOps / Platform Engineering | Jenkins + Harness configuration, deployment policies |
| Company overlay skills | Platform Engineering | Terraform modules, observability templates, security policies |

### How to request changes

To request new patterns, skills, or tools: submit a PR to the AgentCatalyst catalog repo. The platform team reviews weekly. To report Blueprint Advisor quality issues: file a ticket with the spec.md and the generated blueprint. To report Governance Guardian assessment issues: file a ticket with the solution_package JSON and the findings — the EA office reviews assessment logic. See the Operations Runbook for telemetry-driven quality improvement procedures and the Governance Guardian Architecture Extension for assessment procedures.

---

## What AgentCatalyst is NOT

- **Not a deployment tool.** It generates code and pipeline definitions. Your CI/CD deploys.
- **Not a hosting platform.** It doesn't run your agents. Cloud Run + Apigee hosts them.
- **Not a replacement for developers.** It generates a first draft (80-95%). Developers review, refine, and own the code.
- **Not AgentForge.** AgentForge (AnchorOps.ai) uses meta-skills + signed Design Contracts + attestation chains — completely different mechanisms. AgentCatalyst uses Blueprint Advisor RAG + skill-constrained generation. Zero IP overlap.
- **Not a one-size-fits-all template.** Each archetype has its own preset, catalog, and domain skill. The platform adapts.

---

## Production Readiness Checklist

| # | Check | Status |
|---|---|---|
| 1 | All overlay skills pinned to specific versions | ⬜ |
| 2 | Blueprint Advisor MCP Server deployed with OAuth 2.1 | ⬜ |
| 3 | Vertex AI Search data stores populated and search quality validated (≥80% precision) | ⬜ |
| 4 | Company system prompt reviewed by EA + Security | ⬜ |
| 5 | Constitution.md reviewed and approved | ⬜ |
| 6 | Pre-commit evaluation hook tested end-to-end | ⬜ |
| 7 | 3-phase Harness evaluation pipeline tested | ⬜ |
| 8 | Golden dataset baseline established | ⬜ |
| 9 | FNOL reference implementation passing all evaluation gates | ⬜ |
| 10 | 3 additional use cases validated beyond FNOL | ⬜ |
| 11 | Governance Guardian MCP Server deployed with OAuth 2.1 | ⬜ |
| 12 | EA assessment engine connected and returning valid findings for FNOL reference case | ⬜ |
| 13 | Tech Debt Registry table created and accessible | ⬜ |
| 14 | `/catalyst.assess` → `/catalyst.generate` flow tested end-to-end (including showstopper block + tech debt resume) | ⬜ |
| 15 | Developer documentation (dev guide) published | ⬜ |
| 16 | Operations runbook (ops procedures) published | ⬜ |

---

## Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | Blueprint Advisor recommends wrong pattern | Medium | Medium | Confidence scores visible in blueprint. Developer reviews. `validate_composition` catches invalid nesting. Acceptance telemetry tracks accuracy. |
| 2 | Coding agent ignores constitution.md | Low | High | Test with each supported coding agent. Constitution rules are absolute — skills cannot override. |
| 3 | Stale catalogs produce outdated recommendations | Medium | Medium | Weekly catalog health checks. Embedding freshness pipeline. Search quality regression suite. See Operations Runbook. |
| 4 | Business rules too complex for IF/THEN format | Medium | Low | Spec template coaching prompts help developers decompose complex rules. Proprietary algorithms handled as manual P1 tasks (5-20%). |
| 5 | Adoption resistance | Medium | High | Start with high-pain use case (agentic — 4-6 week gap). Demonstrate ROI with FNOL pilot. Let early adopters create pull. |
| 6 | Governance Guardian becomes bottleneck | Medium | Medium | Assessment is async (non-blocking). SA can skip assessment with `/catalyst.generate --skip-assess` (recorded as policy exception). Tech debt path allows proceeding with non-showstoppers. EA office monitors assessment turnaround via telemetry. |

---

## Related Documents

| Document | Audience | What it covers |
|---|---|---|
| **This Architecture Document** | Architects, tech leads | Architectural decisions, layer deep dives, cost model, ROI |
| **AgentCatalyst Developer Guide** (GA) | Developers | Step-by-step walkthroughs, full preset file contents, code examples, spec writing, troubleshooting |
| **AgentCatalyst Operations Runbook** | Platform engineering | Wire-level Vertex AI Search APIs, search quality regression suite, acceptance telemetry, catalog quality engineering, tool lifecycle management, failure modes, escalation matrix, EvalOps operations |
| **Governance Guardian Architecture Extension** | Architects, EA office | `/catalyst.assess` design, async assessment flow, `recordTechDebt` gate in `/catalyst.generate`, Tech Debt Registry, solution package schema, scorecard format |

*Operational procedures (wire-level APIs, regression testing, telemetry, tool lifecycle, failure modes) are maintained in the Operations Runbook to keep this architecture document focused on architectural decisions.*

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
│   ├── catalyst.blueprint.md               ← Custom command: sends spec+plan to Blueprint Advisor
│   ├── catalyst.assess.md                  ← Custom command: sends solution artifacts to Governance Guardian
│   └── catalyst.generate.md                ← Custom command: generates code (with governance gate)
│   └── catalyst.generate.md                ← Custom command: reads blueprint, triggers skill-guided generation (with governance gate)
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

| Component | Source (blueprint section) | Status |
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
  auth: OAuth 2.1 (company SSO)

Call the `submit_spec_and_plan` MCP tool with:
  - spec: contents of spec.md
  - plan: contents of plan.md
  - archetype: from preset.yml (e.g., "agentic")

The MCP server internally runs the Blueprint Advisor LlmAgent:
  1. Queries Vertex AI Search catalogs (patterns, skills, tools)
  2. Applies LLM reasoning guided by company system prompt
  3. Assembles the blueprint markdown
  4. Returns the result via MCP protocol

The coding agent CANNOT access Vertex AI Search directly.
The coding agent CANNOT invoke the LlmAgent directly.
All intelligence lives on the server side, accessed only via MCP tools.```

Connect to the Blueprint Advisor MCP Server:
`mcp://blueprint-advisor.[company-domain].run.app`

Call the `submit_spec_and_plan` MCP tool with the spec and plan contents.
The MCP server handles all internal processing (RAG search, LLM reasoning, blueprint assembly) and returns the result.

Save the response as `app-blueprint.md` in the workspace root.

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
description: Read the markdown blueprint and generate the complete project using skills
usage: /catalyst.generate
---

# /catalyst.generate

Read `app-blueprint.md` from the workspace root.

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

### A.10 FNOL Example: Generated app-blueprint.md

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


---

## Appendix B — Microservice Brownfield Application: Complete Preset & Example Files

*This appendix contains all files for the microservice archetype preset, demonstrated with a Spring Boot + Angular brownfield "Hello World" reference implementation. This preset shares the same company overlay skills as the agentic preset (Appendix A) but uses different templates, catalogs, and domain skills.*

### Directory structure

```
.specify/
├── preset.yml                              ← Microservice preset manifest
├── templates/
│   ├── service-spec-template.md            ← /specify loads this — microservice-specific sections
│   ├── service-plan-template.md            ← /plan loads this — framework + infra questions
│   └── service-tasks-template.md           ← /tasks loads this — generated vs manual work
├── commands/
│   ├── catalyst.blueprint.md               ← Same as agentic (sends spec+plan to Blueprint Advisor)
│   └── catalyst.generate.md                ← Same as agentic (reads YAML, triggers skill-guided gen)
├── memory/
│   ├── springboot-reference.md             ← Spring Boot patterns, annotations, JPA conventions
│   ├── angular-reference.md                ← Angular component patterns, service injection, routing
│   ├── company-patterns.md                 ← SHARED — same company standards as agentic preset
│   ├── approved-tools.md                   ← SHARED — same approved endpoints
│   └── infra-standards.md                  ← SHARED — same Terraform, CI/CD, observability
└── constitution.md                         ← SHARED — same non-negotiable rules
```

---

### B.1 preset.yml (microservice variant)

```yaml
# AgentCatalyst Microservice Preset for GitHub Spec Kit
# Install: specify preset add agentcatalyst-microservice
# Source: github.com/[company]/agentcatalyst-preset-microservice

name: agentcatalyst-microservice
version: "1.0.0"
description: >
  AgentCatalyst accelerator for microservice applications.
  Supports Spring Boot, FastAPI, and Node.js backends with
  Angular, React, or Vue frontends. Brownfield-aware.

archetype: microservice

templates:
  spec: templates/service-spec-template.md
  plan: templates/service-plan-template.md
  tasks: templates/service-tasks-template.md

commands:
  - commands/catalyst.blueprint.md        # SHARED with agentic preset
  - commands/catalyst.generate.md         # SHARED with agentic preset

memory:
  - memory/springboot-reference.md        # Framework-specific
  - memory/angular-reference.md           # Framework-specific
  - memory/company-patterns.md            # SHARED overlay
  - memory/approved-tools.md              # SHARED overlay
  - memory/infra-standards.md             # SHARED overlay

skills:
  domain:
    - name: springboot-service
      version: "2.1.0"
      source: github.com/[company]/skills/springboot-service
    - name: angular-spa
      version: "1.4.0"
      source: github.com/[company]/skills/angular-spa
    - name: jpa-oracle
      version: "1.2.0"
      source: github.com/[company]/skills/jpa-oracle
  overlay:                                # SHARED — identical to agentic preset
    - name: company-terraform
      version: "2.0.0"
    - name: company-observability
      version: "1.3.0"
    - name: company-cicd
      version: "1.5.0"
    - name: company-security
      version: "1.2.0"

settings:
  coding_agents: [copilot, claude-code, gemini-cli, cursor, windsurf]
  output_format: markdown
  save_location: workspace_root
```

---

### B.2 templates/service-spec-template.md

```markdown
---
template: agentcatalyst-service-spec
version: "1.0.0"
description: Structured requirements for microservice applications
usage: Run /specify to fill in this template
---

# Service Specification

## Service Purpose

<!--
Describe what this service does and why it exists.
For BROWNFIELD: state what ALREADY EXISTS and what's NEW.
Use "EXISTING" to mark infrastructure/code that must not be regenerated.
Use "NEW" to mark what needs to be built.

EXAMPLE: "Hello World reference implementation for the Angular + Spring Boot
SPA pattern on ECS Fargate with Oracle RDS. NOT a production application —
a minimal working example that proves every layer of the stack works."
-->

[Describe your service purpose here]

## API Contracts

<!--
List all endpoints with HTTP method, path, request/response bodies.
For BROWNFIELD: mark which endpoints already exist vs are new.

EXAMPLE:
GET  /api/greetings         — list all greetings (NEW)
POST /api/greetings         — create a greeting (NEW)
GET  /api/health            — health check (NEW)
-->

[Define your API contracts here]

## Dependencies

<!--
List all external dependencies: databases, message queues, other services.
For BROWNFIELD: use "EXISTING" + point to the config file.

EXAMPLE: "Oracle RDS — EXISTING database at endpoint configured in
boilerplate/backend/src/main/resources/application.yml.
DO NOT create a new database or modify connection settings."
-->

[List your dependencies here]

## Data Model

<!--
Define entities with fields, types, and constraints.

EXAMPLE:
Greeting: id (NUMBER, auto-generated), name (VARCHAR2 100),
    message (VARCHAR2 500), created_at (TIMESTAMP, auto-generated)
-->

[Define your data model here]

## Frontend Requirements

<!--
For services with a UI component. Describe pages, components, interactions.
For BROWNFIELD: mark which UI elements exist vs are new.

EXAMPLE: "Angular SPA with one page: form with Name + Message fields,
list of submitted greetings below, minimal Angular Material styling."
-->

[Define frontend requirements here — or write N/A if backend-only]

## Infrastructure Requirements

<!--
For GREENFIELD: specify what needs to be provisioned.
For BROWNFIELD: specify "EXISTING infrastructure — DO NOT generate new Terraform."

EXAMPLE: "EXISTING infrastructure — use ECS Fargate + Oracle RDS + ALB
from terraform/. Use existing Dockerfiles from boilerplate/.
Only generate application code."
-->

[Define infrastructure requirements here]

## Business Rules

<!--
Same format as agentic preset — IF/THEN conditions per decision point.
For microservices, these typically cover validation rules, business logic
in service layer, and authorization decisions.

EXAMPLE:
Decision Point: Greeting Validation
  IF name is blank THEN return 400 Bad Request
  IF message length > 500 THEN truncate to 500 characters
-->

[Define your business rules here]

## Error Handling

<!--
Per-dependency timeout, failure, and retry behavior.

EXAMPLE:
Dependency: Oracle RDS
  Timeout: 5 seconds
  On failure: Return 503 Service Unavailable with retry-after header
  Connection pool: HikariCP with max 10 connections
-->

[Define your error handling here]

## Acceptance Criteria

<!--
GIVEN/WHEN/THEN assertions. Generate starter test cases for EvalOps.

EXAMPLE:
GIVEN the service is running
WHEN POST /api/greetings with {"name": "Alice", "message": "Hello"}
THEN return 201 Created with the greeting including generated id
AND the greeting appears in GET /api/greetings response
-->

[Define your acceptance criteria here]
```

---

### B.3 templates/service-plan-template.md

```markdown
---
template: agentcatalyst-service-plan
version: "1.0.0"
description: Technical decisions for microservice applications
usage: Run /plan to answer these questions
---

# Technical Plan

## Backend Framework
- **Framework:** [spring-boot | fastapi | express]
- **Language version:** [e.g., Java 21, Python 3.12, Node 20]
- **Build tool:** [gradle | maven | pip | npm]

## Frontend Framework (if applicable)
- **Framework:** [angular | react | vue | none]
- **Version:** [e.g., Angular 17+]
- **Styling:** [angular-material | tailwind | bootstrap | custom]

## Database
- **Type:** [oracle | postgresql | mysql | mongodb]
- **ORM:** [jpa-hibernate | sqlalchemy | prisma | none]
- **Migration tool:** [flyway | liquibase | alembic | none]
- **Config source:** [new | EXISTING — path to config file]

## Target Platform
- **Runtime:** [ecs_fargate | cloud_run | gke | EXISTING]
- **GCP/AWS Region:** [e.g., us-central1, us-east-1]

## Infrastructure
- **Terraform:** [generate_new | SKIP — existing terraform/]
- **Terraform module source:** [e.g., github.com/[company]/terraform-modules]
- **Docker:** [generate_new | SKIP — existing Dockerfiles]

## CI/CD
- **Pipeline:** [EXISTING | generate_new]
- **Infrastructure pipeline:** [Jenkins]
- **Application pipeline:** [Harness]
- **Deployment strategy:** [canary | blue-green | rolling]

## Observability
- **APM:** [Dynatrace]
- **Tracing:** [OpenTelemetry]
- **Health check path:** [e.g., /api/health]

## EvalOps
- **Test framework:** [junit | pytest | jest]
- **Contract testing:** [pact | spring-cloud-contract | none]
- **Pre-commit threshold:** [e.g., 10% max regression]
```

---

### B.4 templates/service-tasks-template.md

```markdown
---
template: agentcatalyst-service-tasks
version: "1.0.0"
description: Task breakdown for microservice applications
usage: Run /tasks after receiving blueprint
---

# Task Breakdown

## Generated by coding agent (developer reviews)

| Component | Source (blueprint section) | Status |
|---|---|---|
| Controller / route handlers | backend.endpoints: | ⬜ Generated |
| Service layer (business logic first draft) | backend.endpoints: + business_rules: | ⬜ Generated — REVIEW REQUIRED |
| Entity / model classes | backend.entities: | ⬜ Generated |
| Repository / data access | backend.entities: | ⬜ Generated |
| Database migration scripts | backend.entities: | ⬜ Generated |
| DTOs / request-response models | backend.endpoints: | ⬜ Generated |
| Frontend components (if applicable) | frontend: | ⬜ Generated |
| Frontend services + API calls | frontend: | ⬜ Generated |
| Unit tests | acceptance_criteria: | ⬜ Generated |
| Integration tests | acceptance_criteria: | ⬜ Generated |
| Terraform (if greenfield) | infrastructure: | ⬜ Generated or SKIP |
| Dockerfile (if greenfield) | infrastructure: | ⬜ Generated or SKIP |
| CI/CD pipeline (if greenfield) | ci_cd: | ⬜ Generated or SKIP |
| Observability config | observability: | ⬜ Generated |
| Health check endpoint | observability: | ⬜ Generated |

## Developer implements / reviews

| Task | Why | Priority |
|---|---|---|
| Review service layer business logic | First draft from spec rules — refine edge cases | P0 |
| Authentication / authorization | Company-specific SSO/OAuth patterns | P0 |
| Performance tuning | Requires load testing with real data volumes | P1 |
| Custom validation rules | Domain-specific beyond IF/THEN | P1 |
| Error response format | Company API standards | P2 |
```

---

### B.5 memory/ files (microservice-specific)

**memory/springboot-reference.md** — Spring Boot patterns: correct annotations (`@RestController`, `@Service`, `@Repository`, `@Entity`), JPA conventions, Flyway migration naming, `application.yml` structure, health check actuator setup, error handling with `@ControllerAdvice`, request/response DTO patterns, HikariCP connection pool configuration.

**memory/angular-reference.md** — Angular patterns: component structure, service injection with `HttpClient`, reactive forms, routing with lazy loading, Angular Material component usage, proxy configuration for backend API calls, environment-specific configuration, build optimization.

**memory/company-patterns.md** — SHARED with agentic preset (identical file). Company coding standards, naming, error handling, logging.

**memory/approved-tools.md** — SHARED with agentic preset (identical file). Approved endpoints and services.

**memory/infra-standards.md** — SHARED with agentic preset (identical file). Terraform modules, CI/CD templates, observability.

---

### B.6 Hello World Brownfield Example: Filled spec.md

```markdown
# Service Specification — Hello World SPA Reference Implementation

## Service Purpose

Hello World reference implementation for the Angular + Spring Boot SPA
pattern on ECS Fargate with Oracle RDS. This is NOT a production
application — it's a minimal working example that proves every layer
of the stack works end to end.

## API Contracts

GET  /api/greetings         — list all greetings
POST /api/greetings         — create a greeting (body: { "name": "Alice", "message": "Hello" })
GET  /api/greetings/{id}    — get greeting by ID
GET  /api/health            — health check (returns DB connectivity status)

## Dependencies

Oracle RDS — EXISTING database at the endpoint configured in
    boilerplate/backend/src/main/resources/application.yml.
    The agent MUST use the EXISTING datasource configuration.
    DO NOT create a new database or modify the connection settings.

## Data Model

Greeting: id (NUMBER, auto-generated), name (VARCHAR2 100),
    message (VARCHAR2 500), created_at (TIMESTAMP, auto-generated)

## Frontend Requirements

Angular SPA with one page:
    - A form with "Name" and "Message" fields + Submit button
    - A list below showing all submitted greetings (auto-refreshes)
    - Minimal styling using Angular Material
    - Calls backend via /api/greetings (proxied through nginx/ALB)

## Infrastructure Requirements

EXISTING infrastructure — DO NOT generate new Terraform.
Use the existing ECS Fargate + Oracle RDS + ALB from terraform/.
Use the existing Dockerfiles from boilerplate/.
Use the existing CI/CD from ci-cd/.
Only generate application code that runs inside the existing containers.

## Business Rules

Decision Point: Greeting Validation
  Inputs: name, message
  IF name is blank THEN return 400 Bad Request with error "name is required"
  IF message is blank THEN return 400 Bad Request with error "message is required"
  IF message length > 500 THEN truncate to 500 characters with warning
  IF name contains special characters THEN sanitize (strip HTML tags)

## Error Handling

Dependency: Oracle RDS
  Timeout: 5 seconds
  On failure: Return 503 with retry-after header
  Connection pool: HikariCP max 10 connections, min-idle 2

## Acceptance Criteria

GIVEN the service is running and database is accessible
WHEN POST /api/greetings with {"name": "Alice", "message": "Hello"}
THEN return 201 Created with greeting including auto-generated id and created_at

GIVEN one greeting exists in the database
WHEN GET /api/greetings
THEN return 200 with array containing the greeting

GIVEN no greeting with id 999 exists
WHEN GET /api/greetings/999
THEN return 404 Not Found

GIVEN the database is unreachable
WHEN GET /api/health
THEN return 503 Service Unavailable with {"status": "DOWN", "database": "unreachable"}
```

---

### B.7 Hello World Brownfield Example: Generated app-blueprint.md

```yaml
# Generated by Blueprint Advisor
# Spec: spec.md (SHA: xyz789)
# Plan: plan.md (SHA: uvw012)
# Archetype: microservice
# Brownfield: true

archetype: microservice

metadata:
  name: hello-world-spa
  template: springboot-angular
  description: "Hello World ref impl for SPA pattern on ECS Fargate"

platform:
  runtime: ecs_fargate              # EXISTING — do not provision

backend:
  framework: spring-boot
  version: "3.x"
  base_package: com.company.helloworld
  build_tool: gradle                # EXISTING build.gradle

  endpoints:
    - method: GET
      path: /api/greetings
      handler: listGreetings
      description: List all greetings
    - method: POST
      path: /api/greetings
      handler: createGreeting
      description: Create a new greeting
    - method: GET
      path: /api/greetings/{id}
      handler: getGreeting
      description: Get greeting by ID
    - method: GET
      path: /api/health
      handler: healthCheck
      description: Health check with DB status

  entities:
    - name: Greeting
      table: GREETINGS
      fields:
        - { name: id, type: Long, generated: true }
        - { name: name, type: String, length: 100, nullable: false }
        - { name: message, type: String, length: 500, nullable: false }
        - { name: createdAt, type: Timestamp, generated: true }

  business_rules:
    - context: greeting_validation
      rules:
        - "IF name is blank THEN return 400 Bad Request"
        - "IF message is blank THEN return 400 Bad Request"
        - "IF message length > 500 THEN truncate to 500 with warning"
        - "IF name contains special characters THEN sanitize (strip HTML)"

  database:
    type: oracle
    orm: jpa-hibernate
    migration: flyway
    config_source: boilerplate/backend/src/main/resources/application.yml  # EXISTING

frontend:
  framework: angular
  version: "17+"
  styling: angular-material
  pages:
    - name: GreetingPage
      route: /
      components: [GreetingForm, GreetingList]
  proxy:
    target: /api/
    config_source: boilerplate/frontend/proxy.conf.json  # EXISTING

infrastructure:
  terraform:
    action: SKIP                    # EXISTING — do not generate
  docker:
    action: SKIP                    # EXISTING Dockerfiles
  cicd:
    action: SKIP                    # EXISTING Jenkins + Harness

observability:
  apm: dynatrace
  health_check: /api/health
  tracing: opentelemetry

evalops:
  test_framework: junit
  contract_testing: spring-cloud-contract

golden_dataset:
  - given: "service running, DB accessible"
    when: "POST /api/greetings with valid body"
    then: "201 Created with auto-generated id"
  - given: "one greeting exists"
    when: "GET /api/greetings"
    then: "200 with array containing greeting"
  - given: "no greeting with id 999"
    when: "GET /api/greetings/999"
    then: "404 Not Found"
  - given: "database unreachable"
    when: "GET /api/health"
    then: "503 with status DOWN"

patterns_used:
  - pattern: rest-crud
    confidence: high
    rationale: "Standard CRUD endpoints for Greeting entity"
  - pattern: brownfield-integration
    confidence: high
    rationale: "Spec contains EXISTING signals — infrastructure reuse"
  - pattern: spa-backend
    confidence: high
    rationale: "Angular frontend + Spring Boot backend pattern"
```

*End of Appendix B*

