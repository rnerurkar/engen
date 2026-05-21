# AgentCatalyst GA — Developer Guide

*Get from "I need an app" to production-ready generated code in under 1 hour.*
*GA-only — zero pre-GA dependencies.*

> **Companion document:** For architectural depth — pattern catalog, HA/DR matrix, skill mechanism internals, cost analysis, governance model, and risk mitigations — see the *AgentCatalyst Architecture Document* (`agentcatalyst-architecture.md`).

---

## Quick Start (TL;DR)

If you've done this before and just need the commands:

```bash
# 1. Install preset (one-time — pick your archetype)
specify preset add agentcatalyst-agentic      # for AI agents
specify preset add agentcatalyst-microservice  # for microservices

# 2. Create project
mkdir my-app && cd my-app && specify init --preset agentcatalyst-agentic

# 3. Install skills (one-time)
gemini skills install github.com/company/agentcatalyst-skills --scope user

# 4. In VSCode with your coding agent:
/specify              # fill in the structured template → spec.md
/plan                 # answer technical questions → plan.md
/catalyst.blueprint   # Connects to Blueprint Advisor MCP Server (async) → returns app-blueprint.md
# review + edit the markdown blueprint
/catalyst.assess      # Governance Guardian assessment → findings + scorecard (fix + re-assess until passed)
/catalyst.generate    # Governance gate + coding agent generates everything using skills
```

That's it. Your complete project is generated. Skip to [Section 2](#2-greenfield-agentic--fnol-agent-from-scratch) for the full agentic walkthrough, or [Section 3](#3-brownfield-microservices--angular--spring-boot-on-ecs-fargate) for the microservices brownfield example.

---

## Who does what — EA Team vs Developer

### What the EA / Platform Engineering team provides

They've already set up everything you need. You don't configure any of this:

| What they provide | Where it lives | Why you care |
|---|---|---|
| AgentCatalyst presets (per archetype) | Internal preset catalog | You install once — gives you templates, commands, reference docs |
| Pattern catalog (per archetype) | Vertex AI Search | Blueprint Advisor searches this to recommend patterns |
| Domain skills (per archetype) | `github.com/company/agentcatalyst-skills` | Teach the coding agent how to write correct code for ADK, Spring Boot, etc. |
| Company overlay skills (shared) | Same repo | Teach Terraform patterns, Dynatrace config, Jenkins/Harness pipelines, security standards |
| Blueprint Advisor MCP Server | Cloud Run + Cloud Run Jobs (GCP) | LlmAgent exposed as MCP Server (async via MCP Tasks). Your coding agent calls `blueprint_start`, `blueprint_status`, `blueprint_result`, `validate_composition`, `assemble_blueprint` via MCP protocol. |
| Approved tools registry | Apigee API Hub + `memory/approved-tools.md` | What MCP servers, APIs, and A2A agents you can connect to |
| Company Terraform modules | `github.com/company/tf-modules` | Pre-approved infrastructure modules |

### What you (the developer) do

| Step | What you do | Time |
|---|---|---|
| 1 | Install the preset + skills (one-time) | 5 min |
| 2 | `/specify` — describe your problem in structured English | 15 min |
| 3 | `/plan` — answer technical questions | 5 min |
| 4 | `/catalyst.blueprint` — get AI architecture advice | 1–5 min (async, progress in chat) |
| 5 | Review and edit the markdown blueprint | 10 min |
| 5a | **`/catalyst.assess` — governance assessment (iterative)** | **1–5 min per assessment** |
| 6 | `/catalyst.generate` — coding agent generates the project (with governance gate) | 5–10 min |
| 7 | Write business logic + system prompts (the 20%) | 2–4 hours |
| 8 | Commit, PR, CI/CD | Standard process |

---

## 1. Prerequisites

> **Important:** The AgentCatalyst preset includes a `constitution.md` file that encodes non-negotiable rules your coding agent MUST follow (e.g., never deploy directly, always use company Terraform modules, always generate pre-commit hooks). These are coding agent constraints — NOT meta-skills or decision frameworks (those exist only in AgentForge). Your coding agent reads constitution.md before generating any code.

### 1.1 Workstation requirements

| Tool | Version | Install | GA? |
|---|---|---|---|
| VSCode | Latest | https://code.visualstudio.com | N/A |
| A coding agent | Any: GitHub Copilot, Claude Code, Cursor, Gemini CLI | Via VSCode extensions or CLI | N/A |
| Python | 3.10+ | `brew install python` or company dev container | N/A |
| ADK (includes `adk create`) | Latest GA | `pip install google-adk` | ✅ GA |
| `gh` CLI | Latest | `brew install gh` — needed for `gh skill install` | N/A |
| `gcloud` CLI | Latest | `brew install google-cloud-sdk` | ✅ GA |
| Git | Latest | Standard | N/A |

**Not required:** `agents-cli` (pre-GA), `npm`, `npx`. This guide uses only GA tools.

### 1.2 One-time setup

```bash
# 1. Authenticate with GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Authenticate with GitHub (for skill installation)
gh auth login

# 3. Install the ADK (GA — includes adk create)
pip install google-adk

# 4. Install company skills (domain + overlay)
gemini skills install github.com/company/agentcatalyst-skills --scope user

# 5. Verify skills are visible
# In your coding agent, type /skills list — you should see:
#   adk-agents           [user]  ADK agent classes and orchestration
#   adk-tools            [user]  ADK tools — FunctionTool, MCPToolset, AgentTool
#   adk-mcp              [user]  MCP server connections
#   model-armor          [user]  Model Armor content screening
#   company-terraform    [user]  Company Terraform modules
#   company-observability[user]  Dynatrace + Splunk + OTel
#   company-cicd         [user]  Jenkins + Harness (NO direct deploy)
#   company-security     [user]  VPC-SC + CMEK + Secret Manager
```

If skills don't appear, check that `~/.agents/skills/` directory contains the skill folders.

### 1.3 Where skills live on disk

| Scope | Directory | When to use |
|---|---|---|
| **User** (global) | `~/.agents/skills/` | Install once, available in every project |
| **Workspace** (project) | `.agents/skills/` in repo root | Checked into git, available to everyone who clones |

For team-wide consistency, you can also check skills into the project repo:

```bash
cp -r ~/.agents/skills/* .agents/skills/
git add .agents/skills/ && git commit -m "Add company skills"
```

---

## 2. Greenfield Agentic — FNOL Agent from Scratch

This walkthrough builds an AI agent that handles First Notice of Loss (FNOL) for auto insurance from scratch.

### 2.1 Initialize the project

```bash
mkdir fnol-agent && cd fnol-agent
specify init --preset agentcatalyst-agentic
```

This creates the `.specify/` folder with all preset files:

```
fnol-agent/
└── .specify/
    ├── preset.yml
    ├── templates/
    │   ├── spec-template.md
    │   ├── plan-template.md
    │   └── tasks-template.md
    ├── commands/
    │   ├── catalyst.blueprint.md
    │   └── catalyst.generate.md
    └── memory/
        ├── adk-reference.md
        ├── company-patterns.md
        ├── approved-tools.md
        └── infra-standards.md
```

### 2.2 Open in VSCode

```bash
code .
```

Open the Copilot Chat panel (Ctrl+Shift+I or click the chat icon).

### 2.3 `/specify` — Describe the problem

Type `/specify`. The coding agent presents the 6-section template. Fill in each section:

**Business Problem:** "FNOL auto insurance — AI agent handles policyholder accident reports, verifies coverage, collects details, checks fraud, gets repair estimates, routes high-severity to human adjusters."

**Workflow:**
```
1. First, verify the policyholder's identity and active coverage (BigQuery)
2. Then, extract structured incident details from caller description
3. Simultaneously enrich: weather data, police report, fraud scoring, coverage verification
4. Generate claim summary, validate against rubric, refine until quality > 0.85
5. If high severity or fraud score > 0.7, route to human adjuster
```

**Data Sources:** BigQuery (analytical, read-only), Cloud SQL (transactional, read-write), Vertex AI Search (document retrieval)

**External Integrations:** Body shop network (they operate their own quoting service), rental car (they operate their own API), police report (municipal service, we don't control it)

**Internal Capabilities:** Proprietary fraud detection model, proprietary severity classifier, claim notification service

**Infrastructure:** us-central1, gemini-2.0-flash, Jenkins + Harness, Model Armor + DLP + CMEK + VPC-SC

Saved as `spec.md`. (~15 min)

### 2.4 `/plan` — Technical decisions

Type `/plan`. Answer the technical questions:

```
Runtime:         agent_engine
GCP Project:     insurance-agents-prod
Region:          us-central1
Model:           gemini-2.0-flash
Garden Template: adk_a2a
TF Modules:      github.com/company/tf-modules
Jenkins:         agent-infra-plan-apply-v3
Harness:         agent-deploy-canary-v4
Security:        Model Armor yes, DLP yes, CMEK yes, VPC-SC yes
Observability:   Dynatrace yes, OTel yes, Cloud Trace yes
```

Saved as `plan.md`. (~5 min)

### 2.5 `/catalyst.blueprint` — Get AI advice via Blueprint Advisor MCP Server

Type `/catalyst.blueprint`. The coding agent connects to the **Blueprint Advisor MCP Server** and starts a background task.

> **First-time authentication:** The first time you run `/catalyst.blueprint` or `/catalyst.assess`, your coding agent opens a browser for company SSO login (Microsoft Entra ID). After authenticating once (including MFA), tokens are cached securely in your OS keychain. Subsequent commands use silent token refresh — no browser popup. Both the Blueprint Advisor and Governance Guardian share the same OAuth 2.1 authentication, so you authenticate once for both. Tokens last 1 hour with automatic refresh. See Architecture Document, Layer 2 Security for the full OAuth 2.1 flow with Entra ID. You see progress in the Chat pane as the pipeline runs (typically 1–5 minutes). When complete, the coding agent writes several files to your workspace: `app-blueprint.md` (the structured markdown blueprint), component diagram PNGs, HA/DR diagram PNGs, and their editable `.drawio.xml` counterparts — all in your feature directory. The diagrams render inline when you preview the markdown in VSCode.

**Why async?** VS Code Copilot enforces a hard 10–15 second timeout on MCP tool calls. The Blueprint Advisor's internal pipeline (3 RAG searches + LLM reasoning + validation + assembly) takes 15–60 seconds. A single blocking call would be killed before it completes. Instead, the coding agent uses three fast MCP tools — `blueprint_start` (< 2s), `blueprint_status` (< 1s), `blueprint_result` (< 1s) — to drive an async loop. You don't need to think about this; the prompt file handles it automatically.

**What you see in the Chat pane:**

```
You: /catalyst.blueprint

Agent: Blueprint generation started. Checking progress...
Agent: Searching pattern catalog...
Agent: Searching tool registry for BigQuery, Cloud SQL, Vertex AI Search tools...
Agent: Searching skill catalog for matching skills...
Agent: LLM reasoning: mapping tools to agents based on co-occurrence...
Agent: Validating composition...
Agent: Assembling blueprint...
Agent: Blueprint ready! Saved app-blueprint.md to your workspace.

Blueprint Advisor recommends:
  5 agents: LlmAgent (coordinator), SequentialAgent (intake),
            ParallelAgent (enrichment), LoopAgent (summary), LlmAgent (HITL)
  3 MCP servers: bigquery-policy, cloud-sql-claims, vertex-search-policies
  3 A2A agents: body-shop-network, rental-car-service, police-report-service
  3 FunctionTool implementations: severity_classifier, coverage_calculator, notification_sender
  2 skills: bigquery v1.2.0, fraud-detection v2.0.1

Review the markdown and edit before running /catalyst.generate.
```

**What happens behind the scenes:**

1. Your coding agent calls `blueprint_start` with `spec.md` + `plan.md`. The server validates the input, creates a background task, and returns a task ID in under 2 seconds.

2. The background pipeline (running on Cloud Run Jobs with no timeout) does three searches against the company's curated catalogs:

   - **Pattern search** — reads your Workflow section's ordering words ("First," "Simultaneously," "Refine until") and searches the pattern catalog. "First... then..." → Sequential. "Simultaneously" → Parallel. "Refine until" → Loop.

   - **Tool search** — reads your Data Sources and External Integrations sections and searches the tool registry for the specific tools your agent needs. The tool registry is chunked at the **individual tool level**, not the server level — so when you write "BigQuery analytical queries," the search matches the specific `execute_query` tool on the BigQuery MCP server, not just "BigQuery" generically. MCP tools and A2A agent tasks are in the same registry, so one search finds both.

   - **Skill search** — finds skills that match the tools and capabilities your agent needs. Skills are automatically paired with their corresponding tools.

3. Your coding agent polls `blueprint_status` every 10 seconds. Each poll returns the current stage and a progress message displayed in the Chat pane.

4. When the pipeline completes, your coding agent calls `blueprint_result` to retrieve the blueprint and saves it as `app-blueprint.md`.

**How the Blueprint Advisor decides which tool goes to which agent:**

It uses **co-occurrence** — which data source is mentioned in the same sentence as which workflow step. Your spec says: *"First, verify coverage **by querying our BigQuery**."* BigQuery is mentioned in the same sentence as "verify" → BigQuery MCP is assigned to the `verify_policy` agent. This is why the language in your spec matters — clear co-occurrence leads to correct assignments.

### 2.6 Review and edit the markdown blueprint

Open `app-blueprint.md`. The Blueprint Advisor gets it right ~90% of the time. The other 10% is why you review.

**What to check — the assignment audit:**

For each tool in the blueprint, verify the `assigned_to` agent makes sense:

| In the blueprint | Ask yourself | If wrong |
|---|---|---|
| `bigquery-policy → assigned_to: verify_policy` | "Does verify_policy need BigQuery?" Yes — spec says "verify coverage by querying BigQuery" | ✓ Correct |
| `cloud-sql-claims → assigned_to: extract_details` | "Does extract_details write to Cloud SQL?" No — it extracts from caller input. Cloud SQL writes happen at coordinator level. | ✗ Change to `fnol_coordinator` |
| `body-shop-network → assigned_to: enrichment_fan_out` | "Is body shop part of enrichment?" Yes — spec says "simultaneously enrich... body shop" | ✓ Correct |
| `bigquery skill → assigned_to: verify_policy` | "Is the BigQuery skill on the same agent as bigquery-mcp?" Yes — both on verify_policy | ✓ Correct |

**Common assignment mistakes and how to fix them:**

| Mistake | Why it happens | How to fix |
|---|---|---|
| **Write tool on a leaf agent** | Spec says "extract and save" in one sentence — Blueprint Advisor assigns Cloud SQL to `extract_details` | Move `assigned_to` to the coordinator. Write operations are usually coordinator-level. |
| **Tool on wrong parallel branch** | Spec mentions "fraud scoring" and "police report" in the same paragraph — Blueprint Advisor mixes up which goes where | Check which branch name matches the tool's purpose. Edit `assigned_to`. |
| **Missing tool entirely** | Spec mentions a data source the tool registry doesn't have | Add the tool manually to the blueprint. Then request it be added to the registry (see `memory/approved-tools.md`). |
| **MCP when it should be A2A (or vice versa)** | Tool registry has the integration registered as the wrong type | This is rare — the registry determines the type. Report to platform engineering. |
| **Skill on wrong agent** | Skill's `compatible_tools` matched the wrong MCP server | Move the skill's `assigned_to` to match the agent that uses the related tool. |

**Pro tip:** Read the blueprint top-to-bottom and mentally trace the FNOL workflow. For each agent, ask: "Does this agent have access to every data source it needs, and ONLY the data sources it needs?" An agent with too many tools has too much scope. An agent missing a tool will fail at runtime.

### 2.7 `/tasks` — See the breakdown

Type `/tasks`. See the 80/20 split:

**Auto-generated:** Agent classes, MCP connections, A2A clients, Model Armor callbacks, Terraform, Dynatrace, CI/CD pipelines

**You implement:** System prompts, `severity_classifier()`, `coverage_calculator()`, `notification_sender()`, test data

### 2.7a `/catalyst.assess` — Governance assessment

→ *Governance Guardian Architecture Extension covers the full assessment flow, solution package schema, and scorecard format.*

After reviewing and editing the blueprint, run the governance assessment before generating code:

```
/catalyst.assess
```

The coding agent extracts solution artifacts from your workspace — TSA component diagram from your drawio file, HA/DR views, sequence diagrams (mermaid), NFRs, architecture decisions log, tech stack, and patterns used — packages them as JSON, and sends them to the **Governance Guardian MCP Server** using the same async pattern as the Blueprint Advisor (`assess_start` → poll → `assess_result`).

**What you see in the Chat pane:**

```
You: /catalyst.assess

Agent: Extracting solution artifacts from workspace...
       ✓ TSA component diagram (claims-portal-tsa.drawio.xml)
       ✓ HA/DR views (2 views found)
       ✓ Sequence diagrams (3 mermaid files)
       ✓ NFRs (from plan.md)
       ✓ Architecture Decisions Log (4 entries from adl.md)
       ✓ Tech stack (from app-blueprint.md)
       ✓ Patterns used (3 patterns)

       Governance assessment started. Checking progress...
       Evaluating architecture compliance...
       Checking pattern adherence...
       Scoring HA/DR readiness...
       Assessment complete!

       SCORECARD: 72/100 (Grade C)
       🔴 SHOWSTOPPER: F-001 — No cross-region DR for Aurora PostgreSQL (ADR-205)
       🟠 HIGH: F-002 — WAF rules not using enterprise managed rule group
       🟡 MEDIUM: F-003 — Angular 17 not on approved tech radar

       Fix the showstopper and run /catalyst.assess again.
```

**The assess-fix loop:** Fix the showstopper findings in your workspace (update Terraform, drawio diagrams, etc.), then run `/catalyst.assess` again. Repeat until no showstoppers remain. Non-showstopper findings will be recorded as tech debt when you run `/catalyst.generate`.

**Missing artifacts:** If the coding agent can't find a drawio file or NFR section, it includes the artifact as `null` with a reason. The Governance Guardian will likely flag missing artifacts as findings.

### 2.8 `/catalyst.generate` — Generate everything

Type `/catalyst.generate`. **Before the generation pipeline runs**, the coding agent makes one call to the Governance Guardian — `recordTechDebt`. This checks whether any showstopper findings remain from your latest `/catalyst.assess` run:

- **If showstoppers exist → BLOCKED.** The coding agent reports the showstoppers and tells you to fix them and re-run `/catalyst.assess`.
- **If no showstoppers → RESUME.** Remaining findings are recorded as tech debt (you'll see the tech debt ID). Code generation proceeds.
- **If no assessment exists → WARNING.** The coding agent suggests running `/catalyst.assess` first, or you can type `skip` to proceed without governance assessment.

```
You: /catalyst.generate

Agent: Checking governance gate...
       Governance passed. Tech debt recorded (TD-2026-0142):
       - F-002: WAF managed rule group (HIGH) — tech debt
       - F-003: Angular 17 tech radar (MEDIUM) — tech debt
       Proceeding with code generation...
```

The coding agent then reads the blueprint and uses installed skills to generate the project:

```
fnol-agent/
├── app/
│   ├── agent.py                          ← Root LlmAgent
│   ├── sub_agents/
│   │   ├── intake_pipeline.py            ← SequentialAgent
│   │   ├── enrichment_fan_out.py         ← ParallelAgent
│   │   ├── claim_summary_loop.py         ← LoopAgent
│   │   └── adjuster_review.py            ← HITL
│   ├── mcp_connections/
│   │   ├── bigquery_policy.py            ← MCPToolset
│   │   ├── cloud_sql_claims.py           ← MCPToolset
│   │   └── vertex_search_policies.py     ← MCPToolset
│   ├── a2a_clients/
│   │   ├── body_shop_network.py          ← AgentTool
│   │   ├── rental_car_service.py         ← AgentTool
│   │   └── police_report_service.py      ← AgentTool
│   ├── tools/
│   │   ├── severity_classifier.py        ← YOUR CODE HERE
│   │   ├── coverage_calculator.py        ← YOUR CODE HERE
│   │   └── notification_sender.py        ← YOUR CODE HERE
│   ├── callbacks/
│   │   └── model_armor.py                ← Standard screening
│   └── skills/
│       ├── bigquery/
│       └── fraud-detection/
├── deployment/terraform/
│   ├── main.tf                           ← Company TF modules (via GitHub URLs)
│   ├── variables.tf                      ← Descriptions from module repos
│   ├── terraform.tfvars                  ← Pre-filled from blueprint
│   ├── versions.tf                       ← Provider versions pinned
│   ├── backend.tf                        ← GCS backend config
│   ├── environments/
│   │   ├── dev.tfvars
│   │   ├── staging.tfvars
│   │   └── prod.tfvars                   ← Multi-region for production
│   └── dr/
│       ├── failover.tf                   ← From blueprint §13 lifecycle
│       ├── failback.tf
│       └── lifecycle.tf
├── observability/
│   ├── dynatrace/
│   └── otel/
├── ci-cd/
│   ├── Jenkinsfile                       ← Company template ref
│   └── harness-pipeline.yaml             ← Canary deployment
├── pyproject.toml
├── README.md
└── app-blueprint.md
```

**What `/catalyst.generate` did NOT do:**
- It did NOT deploy to GCP — no `agents-cli deploy`, no direct provisioning
- It did NOT generate Cloud Build config — company uses Jenkins
- It generated Jenkinsfile + harness-pipeline.yaml instead — your CI/CD takes over after you merge

#### What the generated code looks like

**Agent class** (guided by `adk-agents` skill):

```python
# app/sub_agents/intake_pipeline.py
from google.adk.agents import SequentialAgent

intake_pipeline = SequentialAgent(
    name="intake_pipeline",
    sub_agents=["verify_policy", "extract_details"],
    description="Ordered intake — verify policy then extract incident details",
)
```

**MCP connection** (guided by `adk-mcp` skill):

```python
# app/mcp_connections/bigquery_policy.py
from google.adk.tools import MCPToolset

bigquery_policy = MCPToolset(
    name="bigquery-policy",
    connection_params={
        "endpoint": "bigquery.googleapis.com",
        "transport": "sse",
        "auth": "workload_identity",
    },
    description="Query policy data warehouse",
)
```

**Terraform module** (guided by `company-terraform` skill):

```hcl
# deployment/terraform/main.tf
module "agent-runtime" {
  source  = "github.com/company/tf-modules//agent-runtime?ref=v3.1.0"
  project = var.gcp_project
  region  = var.gcp_region
  agent_name = "fnol-coordinator"
}
```

#### How Terraform generation works behind the scenes

When `/catalyst.generate` runs, the IaC overlay skill (`company-terraform`) reads `app-blueprint.md` §8 (Infrastructure Modules) and generates all the Terraform by following these steps:

1. **Reads the module URLs from your blueprint** — §8 lists GitHub URLs for each company Terraform module needed by your solution (e.g., `github.com/company/tf-agentic-pilot-cold` for the overall pattern, `github.com/company/tf-cloud-sql` for the claims database).

2. **Reads module interfaces via GitHub MCP Server** — Your coding agent calls the GitHub MCP Server to read `variables.tf` and `outputs.tf` from each module repo. This tells it what parameters each module needs. It also reads `examples/` for reference values. Your GitHub authentication is used — no separate credentials needed.

3. **Maps your blueprint to module variables** — The skill deterministically maps blueprint fields to Terraform variables. For example: §10 NFRs says "availability: 99.95%" → `ha_enabled = true`. §1 Metadata says "DR strategy: Pilot Light" → selects the `tf-agentic-pilot-cold` pattern repo. §3 Agent Topology agent names → one Cloud Run service per agent.

4. **Generates the complete Terraform project:**

```
deployment/terraform/
├── main.tf             ← Root module: references company modules via GitHub URLs
├── variables.tf        ← All variables with descriptions from module repos
├── terraform.tfvars    ← Pre-filled from your blueprint (regions, project, DR)
├── outputs.tf          ← Values exported for CI/CD pipeline to consume
├── versions.tf         ← Provider versions pinned from module repos
├── backend.tf          ← GCS backend for state
├── environments/
│   ├── dev.tfvars      ← Single-region, minimal resources
│   ├── staging.tfvars  ← Single-region, production-like
│   └── prod.tfvars     ← Multi-region, full DR
└── dr/
    ├── failover.tf     ← Failover triggers from blueprint §13
    ├── failback.tf     ← Failback procedure resources
    └── lifecycle.tf    ← All 4 lifecycle scenarios
```

5. **Wires modules together** — The generated `main.tf` references each company module with a pinned version and passes in variables from your blueprint. Module outputs are wired to inputs (e.g., Cloud SQL connection string → agent environment variable):

```hcl
# deployment/terraform/main.tf — GENERATED, DO NOT EDIT MANUALLY
module "claims_db" {
  source         = "github.com/company/tf-cloud-sql?ref=v3.1.0"
  instance_name  = "${var.project_name}-claims-db"
  region         = var.primary_region
  ha_enabled     = true              # From blueprint §10: 99.95% availability
  replica_region = var.dr_region     # From blueprint §10: RPO < 1 hour
}

module "agent_stack" {
  source         = "github.com/company/tf-agentic-pilot-cold?ref=v2.3.0"
  project_name   = var.project_name
  primary_region = var.primary_region
  dr_region      = var.dr_region
  services = {
    fnol_coordinator = { cpu = "2", memory = "4Gi", min = 2, max = 10 }
    extract_details  = { cpu = "1", memory = "2Gi", min = 1, max = 5 }
    # ... one entry per agent from blueprint §3
  }
  db_connection_string = module.claims_db.connection_string  # wired
}
```

**The critical rule:** Your coding agent will **never** generate raw `google_*` or `aws_*` Terraform resources. It always references company modules from the GitHub URLs in your blueprint. This is enforced by the `company-terraform` skill. If a module doesn't exist for something your solution needs, the generated code includes a `# TODO: Request tf-{service} module from platform team` comment instead of guessing.

**If you need to customize Terraform:** Edit `terraform.tfvars` to change values (regions, instance sizes). To change the module structure itself, edit `main.tf` — but be aware that `/catalyst.generate` will overwrite it if you re-run. For persistent customizations, request module parameter additions from the platform team.

**Jenkinsfile** (guided by `company-cicd` skill):

```groovy
// ci-cd/Jenkinsfile — DO NOT use agents-cli deploy
@Library('company-pipeline-lib') _
agentInfraPlanApply(
    template: 'agent-infra-plan-apply-v3',
    terraformDir: 'deployment/terraform',
    environment: params.ENVIRONMENT
)
```

### 2.9 Write the 20%

**System prompts** — open each agent class and replace `<<< ENGINEER MUST WRITE >>>`:

```python
# app/agent.py
fnol_coordinator = LlmAgent(
    name="fnol_coordinator",
    model="gemini-2.0-flash",
    system_instruction="""You are the FNOL Coordinator for auto insurance.
    When a policyholder reports an accident, orchestrate: verify coverage
    (intake_pipeline), enrich from external sources (enrichment_fan_out),
    summarize (claim_summary_loop), route high-severity to adjuster
    (adjuster_review). Be professional, empathetic, thorough.""",
    sub_agents=[intake_pipeline, enrichment_fan_out,
                claim_summary_loop, adjuster_review],
)
```

**FunctionTool bodies** — implement business logic:

```python
# app/tools/severity_classifier.py
def severity_classifier(claim_data: dict) -> dict:
    """Classify claim severity."""
    damage = claim_data.get("estimated_damage", 0)
    injuries = claim_data.get("injuries_reported", False)
    if injuries or damage > 25000:
        return {"severity": "high", "confidence": 0.92}
    elif damage > 5000:
        return {"severity": "medium", "confidence": 0.85}
    else:
        return {"severity": "low", "confidence": 0.95}
```

### 2.10 Commit and CI/CD

```bash
git add . && git commit -m "feat: FNOL agent generated by AgentCatalyst"
git push origin feature/fnol-agent
# Open PR → Team reviews → Merge
# Jenkins runs Terraform → Harness deploys Non-Prod → Pre-Prod → Prod
```

---

## 3. Brownfield Microservices — Angular + Spring Boot on ECS Fargate

This section walks through a real-world brownfield scenario: your company has an existing SPA (Single Page Application) pattern with Angular frontend and Spring Boot backend running on ECS Fargate, connecting to Oracle RDS. There's existing IaC and boilerplate integration code, but **no "Hello World" reference implementation** that developers can clone and start building from.

### 3.1 What already exists

The platform engineering team has built the infrastructure layer and boilerplate, but stopped short of a working application:

```
existing-spa-pattern/
├── terraform/                         ← EXISTS: IaC for the full stack
│   ├── modules/
│   │   ├── ecs-fargate/               ← ECS cluster, task definitions, services
│   │   ├── oracle-rds/                ← Oracle RDS instance, subnet groups, security groups
│   │   ├── alb/                       ← Application Load Balancer, target groups, listeners
│   │   ├── ecr/                       ← Container registries (frontend + backend)
│   │   ├── vpc/                       ← VPC, subnets, NAT gateway, route tables
│   │   └── cloudwatch/                ← Log groups, dashboards, alarms
│   ├── environments/
│   │   ├── dev.tfvars
│   │   ├── staging.tfvars
│   │   └── prod.tfvars
│   └── main.tf                        ← Root module wiring all components
│
├── boilerplate/                       ← EXISTS: Integration code only
│   ├── backend/
│   │   ├── src/main/resources/
│   │   │   └── application.yml        ← Oracle datasource config (JDBC URL,
│   │   │                                 connection pool, HikariCP settings)
│   │   ├── Dockerfile                 ← Multi-stage build for Spring Boot
│   │   └── build.gradle               ← Dependencies (spring-boot-starter-web,
│   │                                     spring-boot-starter-data-jpa, ojdbc11)
│   └── frontend/
│       ├── proxy.conf.json            ← Angular dev server → backend proxy config
│       ├── Dockerfile                 ← Multi-stage build for Angular (nginx)
│       ├── nginx.conf                 ← Production nginx config (routing, gzip, headers)
│       └── angular.json               ← Angular workspace config
│
├── ci-cd/                             ← EXISTS: Pipeline definitions
│   ├── Jenkinsfile                    ← Terraform plan + apply
│   └── harness-pipeline.yaml          ← ECS Fargate blue-green deployment
│
└── docs/
    └── architecture.md                ← Pattern documentation
```

**What EXISTS:** Complete Terraform for ECS Fargate + Oracle RDS + ALB + VPC. Dockerfiles for both frontend and backend. Spring Boot `application.yml` with Oracle datasource configured. Angular proxy and nginx configs. Jenkins + Harness pipelines.

**What's MISSING:** There is no actual application code. No Spring Boot controllers, services, repositories, or entities. No Angular components, services, routes, or pages. A developer who clones this repo can provision the infrastructure and build empty containers — but the containers do nothing. There's no "Hello World" that proves the stack works end to end.

### 3.2 What needs to be built — the Hello World reference implementation

The "Hello World" reference implementation should prove that every layer works together:

| Layer | What needs to exist | Purpose |
|---|---|---|
| **Angular frontend** | A simple page with a form that submits data and displays a response | Proves: Angular → nginx → ALB → Spring Boot round-trip works |
| **Spring Boot backend** | A REST controller with GET and POST endpoints, a JPA entity, a repository, a service | Proves: Spring Boot → Oracle RDS round-trip works |
| **Database** | A Flyway migration creating one table + seed data | Proves: Schema management works, Oracle connection works |
| **End-to-end** | The form submits data, backend stores in Oracle, backend returns it, frontend displays it | Proves: The entire stack works top to bottom |

### 3.3 Step-by-step: Creating the Hello World with AgentCatalyst

#### Step 1: Initialize AgentCatalyst in the existing repo

```bash
cd existing-spa-pattern
specify init --preset agentcatalyst-microservice
```

This adds the `.specify/` folder alongside the existing `terraform/`, `boilerplate/`, and `ci-cd/` directories. It doesn't modify any existing files.

#### Step 2: `/specify` — Describe the Hello World

Type `/specify` in your coding agent. Fill in the microservice template:

```markdown
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
```

**Key language:** Notice the repeated "EXISTING" and "DO NOT create new" signals. This tells the Blueprint Advisor MCP Server (which the coding agent invokes via `blueprint_start`) and the coding agent to work within the existing infrastructure, not generate new infrastructure.

#### Step 3: `/plan` — Technical decisions

```
Runtime:           ecs_fargate (EXISTING)
Backend framework: Spring Boot 3.x (EXISTING build.gradle)
Frontend framework: Angular 17+ (EXISTING angular.json)
Database:          Oracle RDS (EXISTING — use boilerplate/application.yml)
Terraform:         SKIP — infrastructure already exists
CI/CD:             EXISTING Jenkinsfile + harness-pipeline.yaml
```

#### Step 4: `/catalyst.blueprint` — Get AI advice via MCP (async)

The Blueprint Advisor reads the spec and recognizes the brownfield signals. Like the greenfield flow (see §2.5 for the full async explanation), your coding agent starts a background task, polls for progress, and retrieves the result. You see progress in the Chat pane:

```
Agent: Blueprint generation started. Checking progress...
Agent: Searching pattern catalog for microservice patterns...
Agent: Searching tool registry — recognizing EXISTING signals for Oracle, Angular, ECS...
Agent: Reasoning: brownfield mode — skipping infrastructure generation...
Agent: Assembling blueprint...
Agent: Blueprint ready! Saved app-blueprint.md.
```

This typically takes 1–3 minutes for a brownfield spec. The returned `app-blueprint.md` references existing infrastructure rather than creating new infrastructure:

```yaml
metadata:
  name: hello-world-spa
  archetype: microservice
  template: springboot-angular
  description: "Hello World ref impl for SPA pattern on ECS Fargate"

platform:
  runtime: ecs_fargate    # EXISTING — do not provision

backend:
  framework: spring-boot
  base_package: com.company.helloworld
  endpoints:
    - method: GET
      path: /api/greetings
      handler: listGreetings
    - method: POST
      path: /api/greetings
      handler: createGreeting
    - method: GET
      path: /api/greetings/{id}
      handler: getGreeting
    - method: GET
      path: /api/health
      handler: healthCheck

  entities:
    - name: Greeting
      table: GREETINGS
      fields:
        - { name: id, type: Long, generated: true }
        - { name: name, type: String, length: 100 }
        - { name: message, type: String, length: 500 }
        - { name: createdAt, type: Timestamp, generated: true }

  database:
    type: oracle
    config_source: boilerplate/backend/src/main/resources/application.yml
    migration_tool: flyway

frontend:
  framework: angular
  pages:
    - name: greetings
      path: /
      components: [greeting-form, greeting-list]
  ui_library: angular-material
  api_proxy: boilerplate/frontend/proxy.conf.json

infrastructure:
  terraform:
    action: SKIP      # Infrastructure already exists
  security:
    existing: true    # Use existing VPC, security groups
  observability:
    cloudwatch: true  # Use existing CloudWatch config
  cicd:
    action: SKIP      # Pipeline definitions already exist
```

**Notice:** `infrastructure.terraform.action: SKIP` and `infrastructure.cicd.action: SKIP` — the Blueprint Advisor recognized the brownfield signals and excluded infrastructure generation.

#### Step 5: Review the markdown

Verify:
- `database.config_source` points to the correct `application.yml`
- Entity fields match your Oracle column types
- Frontend proxy references the existing `proxy.conf.json`
- Infrastructure is marked SKIP

#### Step 6: `/catalyst.generate` — Generate the application code

Type `/catalyst.generate`. The coding agent reads the blueprint and uses skills to generate **only the application code** — no infrastructure, no CI/CD, no Docker configs (those already exist):

```
existing-spa-pattern/
├── terraform/                         ← UNTOUCHED (exists)
├── boilerplate/                       ← UNTOUCHED (exists)
├── ci-cd/                             ← UNTOUCHED (exists)
│
├── backend/                           ← NEW: Generated Spring Boot app
│   ├── src/main/java/com/company/helloworld/
│   │   ├── HelloWorldApplication.java       ← Spring Boot main class
│   │   ├── controller/
│   │   │   └── GreetingController.java      ← REST controller (4 endpoints)
│   │   ├── service/
│   │   │   └── GreetingService.java         ← Business logic
│   │   ├── repository/
│   │   │   └── GreetingRepository.java      ← JPA repository (Spring Data)
│   │   ├── entity/
│   │   │   └── Greeting.java                ← JPA entity mapped to GREETINGS table
│   │   ├── dto/
│   │   │   ├── GreetingRequest.java         ← Request DTO with validation
│   │   │   └── GreetingResponse.java        ← Response DTO
│   │   └── health/
│   │       └── OracleHealthIndicator.java   ← DB connectivity health check
│   ├── src/main/resources/
│   │   ├── application.yml                  ← SYMLINK to boilerplate version
│   │   └── db/migration/
│   │       └── V1__create_greetings.sql     ← Flyway migration
│   └── src/test/java/com/company/helloworld/
│       ├── controller/
│       │   └── GreetingControllerTest.java  ← Unit tests
│       └── integration/
│           └── GreetingIntegrationTest.java ← Integration test with Oracle
│
├── frontend/                          ← NEW: Generated Angular app
│   ├── src/app/
│   │   ├── app.component.ts                 ← Root component
│   │   ├── app.module.ts                    ← Module with Material imports
│   │   ├── app-routing.module.ts            ← Routes
│   │   ├── components/
│   │   │   ├── greeting-form/
│   │   │   │   ├── greeting-form.component.ts
│   │   │   │   ├── greeting-form.component.html
│   │   │   │   └── greeting-form.component.css
│   │   │   └── greeting-list/
│   │   │       ├── greeting-list.component.ts
│   │   │       ├── greeting-list.component.html
│   │   │       └── greeting-list.component.css
│   │   ├── services/
│   │   │   └── greeting.service.ts          ← HTTP client for /api/greetings
│   │   └── models/
│   │       └── greeting.model.ts            ← TypeScript interface
│   ├── proxy.conf.json                      ← SYMLINK to boilerplate version
│   └── angular.json                         ← EXTENDED from boilerplate version
│
├── docs/
│   └── hello-world-readme.md          ← NEW: How to run the Hello World
│
└── .specify/                          ← AgentCatalyst preset
```

**What was generated:** Spring Boot application code (controller, service, repository, entity, DTOs, health check, Flyway migration, tests) + Angular application code (components, services, models, routing). Everything needed to make the existing infrastructure actually serve a working application.

**What was NOT generated:** No new Terraform. No new Dockerfiles. No new CI/CD pipelines. No new database instances. The generated code plugs into the existing infrastructure.

#### What the generated brownfield code looks like

**Spring Boot REST controller** (guided by `spring-boot` domain skill):

```java
// backend/src/main/java/com/company/helloworld/controller/GreetingController.java
@RestController
@RequestMapping("/api/greetings")
public class GreetingController {

    private final GreetingService greetingService;

    public GreetingController(GreetingService greetingService) {
        this.greetingService = greetingService;
    }

    @GetMapping
    public List<GreetingResponse> listGreetings() {
        return greetingService.findAll();
    }

    @PostMapping
    public GreetingResponse createGreeting(@Valid @RequestBody GreetingRequest request) {
        return greetingService.create(request);
    }

    @GetMapping("/{id}")
    public GreetingResponse getGreeting(@PathVariable Long id) {
        return greetingService.findById(id);
    }
}
```

**JPA entity** (mapped to Oracle GREETINGS table):

```java
// backend/src/main/java/com/company/helloworld/entity/Greeting.java
@Entity
@Table(name = "GREETINGS")
public class Greeting {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(length = 100, nullable = false)
    private String name;

    @Column(length = 500, nullable = false)
    private String message;

    @Column(name = "CREATED_AT", updatable = false)
    @CreationTimestamp
    private Timestamp createdAt;

    // getters, setters omitted
}
```

**Flyway migration** (creates the table in Oracle on first boot):

```sql
-- backend/src/main/resources/db/migration/V1__create_greetings.sql
CREATE TABLE GREETINGS (
    id         NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       VARCHAR2(100)  NOT NULL,
    message    VARCHAR2(500)  NOT NULL,
    created_at TIMESTAMP      DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- Seed data for verification
INSERT INTO GREETINGS (name, message) VALUES ('System', 'Hello World — stack verified');
```

**Angular component** (the greeting form):

```typescript
// frontend/src/app/components/greeting-form/greeting-form.component.ts
@Component({
  selector: 'app-greeting-form',
  templateUrl: './greeting-form.component.html',
})
export class GreetingFormComponent {
  name = '';
  message = '';

  constructor(private greetingService: GreetingService) {}

  onSubmit(): void {
    this.greetingService
      .create({ name: this.name, message: this.message })
      .subscribe(() => {
        this.name = '';
        this.message = '';
        this.greetingService.refresh$.next();
      });
  }
}
```

**Angular HTTP service** (calls backend through nginx/ALB proxy):

```typescript
// frontend/src/app/services/greeting.service.ts
@Injectable({ providedIn: 'root' })
export class GreetingService {
  private apiUrl = '/api/greetings';  // proxied to backend via proxy.conf.json
  refresh$ = new Subject<void>();

  constructor(private http: HttpClient) {}

  findAll(): Observable<Greeting[]> {
    return this.http.get<Greeting[]>(this.apiUrl);
  }

  create(request: { name: string; message: string }): Observable<Greeting> {
    return this.http.post<Greeting>(this.apiUrl, request);
  }
}
```

Every generated file uses the **existing** `application.yml` for Oracle connectivity and the **existing** `proxy.conf.json` for API routing. No new infrastructure was created.

#### Step 7: Verify the integration points

Before committing, verify that the generated code connects to the existing infrastructure:

| Integration point | Generated code | Existing infrastructure | What to verify |
|---|---|---|---|
| **Oracle connection** | `application.yml` symlinks to boilerplate version | Oracle RDS endpoint in boilerplate `application.yml` | JDBC URL, credentials in Secrets Manager, HikariCP pool settings |
| **Docker build** | `HelloWorldApplication.java` is the main class | Existing `Dockerfile` runs `gradle bootJar` and expects main class | Ensure main class path matches Dockerfile `ENTRYPOINT` |
| **ALB routing** | Controller maps to `/api/greetings` | Existing ALB listener rules route `/api/*` to backend target group | Ensure path prefix matches ALB rules |
| **Angular proxy** | `greeting.service.ts` calls `/api/greetings` | Existing `proxy.conf.json` forwards `/api` to backend | Ensure proxy target matches backend container port |
| **Flyway migration** | `V1__create_greetings.sql` creates `GREETINGS` table | Existing Oracle RDS accepts DDL from application | Ensure Flyway is enabled in `application.yml` (`spring.flyway.enabled=true`) |

#### Step 8: Run locally (optional)

For local development, you need an Oracle-compatible database. Two options:

**Option A — Oracle XE in Docker (recommended):**

```bash
# Start Oracle XE locally
docker run -d --name oracle-xe \
  -p 1521:1521 \
  -e ORACLE_PASSWORD=localdev \
  container-registry.oracle.com/database/express:21.3.0-xe

# Create a local Spring Boot profile
cat > backend/src/main/resources/application-local.yml << EOF
spring:
  datasource:
    url: jdbc:oracle:thin:@localhost:1521/XEPDB1
    username: system
    password: localdev
  flyway:
    enabled: true
EOF
```

**Option B — H2 in Oracle compatibility mode (faster, no Docker):**

```bash
cat > backend/src/main/resources/application-local.yml << EOF
spring:
  datasource:
    url: jdbc:h2:mem:testdb;MODE=Oracle
    driver-class-name: org.h2.Driver
  jpa:
    database-platform: org.hibernate.dialect.H2Dialect
  flyway:
    enabled: true
EOF
```

**Run the stack locally:**

```bash
# Backend (uses local profile)
cd backend
SPRING_PROFILES_ACTIVE=local ./gradlew bootRun

# Frontend (separate terminal — proxies /api to localhost:8080)
cd frontend
ng serve --proxy-config proxy.conf.json

# Open http://localhost:4200 — submit a greeting, see it in the list
```

#### Step 9: Commit and deploy

```bash
git add backend/ frontend/ docs/
git commit -m "feat: Hello World ref impl for SPA pattern"
git push origin feature/hello-world-ref-impl
# Open PR → Team reviews → Merge
# EXISTING Jenkins pipeline runs Terraform (no changes) + builds Docker images
# EXISTING Harness pipeline deploys to ECS Fargate (blue-green)
```

The existing CI/CD pipelines handle everything — they build the Docker images using the existing Dockerfiles (which now have actual application code inside), push to existing ECR repos, and deploy to existing ECS Fargate services.

### 3.4 What the Hello World proves

| Layer | Before (IaC only) | After (Hello World) |
|---|---|---|
| **Angular → nginx** | nginx serves empty page | nginx serves Angular app with form + list |
| **nginx → ALB** | ALB routes to empty backend | ALB routes to Spring Boot with real endpoints |
| **ALB → Spring Boot** | Spring Boot starts but has no endpoints | 4 REST endpoints responding to requests |
| **Spring Boot → Oracle** | Datasource configured but no queries | JPA repository performing CRUD on GREETINGS table |
| **Flyway → Oracle** | No migrations exist | Schema auto-created on first boot |
| **End-to-end** | Infrastructure runs but does nothing | User submits greeting → stored in Oracle → displayed in UI |

**The Hello World is the missing proof that the entire stack works.** Any developer building a real application on this pattern can now clone the Hello World, see every integration working, and modify it for their use case.

---

## 4. Writing Effective Specs — Signal Words That Help

> For the full list of 11 agentic patterns and how the Blueprint Advisor selects them, see the Architecture Document (Layer 2 section).

### Words that trigger pattern selection

The Blueprint Advisor reads your Workflow section and searches the pattern catalog. These words help it find the right patterns:

| What you write | What the Blueprint Advisor searches for | Pattern found |
|---|---|---|
| "First... Then... After that" | `sequential ordered dependency` | SequentialAgent |
| "Simultaneously" / "In parallel" | `parallel concurrent independent` | ParallelAgent |
| "Generate... validate... refine until" | `loop iterative threshold` | LoopAgent |
| "If [condition], route to [human]" | `human approval async routing` | HITL (LlmAgent + LongRunningFunctionTool) |
| "Coordinate across multiple domains" | `coordinator dispatcher multi-domain` | LlmAgent as root with sub_agents |
| "Search documents and reason" | `agentic RAG retrieval reasoning` | LlmAgent + Vertex AI Search |

### Words that trigger tool discovery

The Blueprint Advisor reads your Data Sources and External Integrations sections and searches the tool registry. The tool registry is chunked at the **individual tool level** — so specific language helps it find the exact tool, not just the server:

| What you write | What the Blueprint Advisor searches for | What it finds |
|---|---|---|
| "BigQuery — analytical queries, read-only" | `BigQuery analytical query read-only` | `execute_query` tool on bigquery-mcp server |
| "Cloud SQL — create claim records, transactional" | `Cloud SQL transactional INSERT UPDATE` | `execute_sql` tool on cloudsql-mcp server |
| "Search policy documents for coverage" | `Vertex AI Search document retrieval` | `search_documents` tool on vertex-search-mcp |
| "body shop — they operate their own quoting service" | `body shop repair estimate` | `get_repair_estimate` task on body-shop-network A2A agent |
| "our proprietary fraud detection model" | (no search — ownership signal) | FunctionTool implementation (first draft generated from spec rules; you review and refine) |

**Key distinction — ownership signals determine MCP vs A2A:**

| What you write | Blueprint Advisor infers | Connection type |
|---|---|---|
| "BigQuery" / "Cloud SQL" / "our data warehouse" | We operate it | MCP server (`MCPToolset`) |
| "they operate their own" / "partner API" / "municipal system" | External partner | A2A agent (`AgentTool`) |
| "our proprietary" / "internal model" | Company-owned logic | FunctionTool implementation (first draft from spec rules; no external connection) |

You don't need to specify whether something is MCP or A2A. The tool registry knows. Just describe what it is and who operates it.

### Words that drive correct tool-to-agent assignment

The Blueprint Advisor assigns tools to agents based on **co-occurrence** — which data source you mention in the same sentence as which workflow step. This is why sentence structure matters:

**Good — clear co-occurrence (Blueprint Advisor assigns correctly):**

```markdown
## Workflow
1. First, verify the policyholder's coverage by querying our BigQuery
   policy data warehouse.
```

The Blueprint Advisor reads: "verify" (→ agent: verify_policy) + "BigQuery" (→ tool: bigquery-mcp) in the same sentence → assigns bigquery-mcp to verify_policy. ✅

**Bad — ambiguous co-occurrence (Blueprint Advisor may assign incorrectly):**

```markdown
## Workflow
1. First, verify the policyholder's coverage.
## Data Sources
- BigQuery — policy data warehouse
```

BigQuery is mentioned in the Data Sources section, not in the workflow step. The Blueprint Advisor doesn't know which agent needs BigQuery — it might assign it to the root coordinator instead of verify_policy. ❌

**Fix:** Mention the data source **in the workflow step** where it's used, not just in the Data Sources section.

### Words that help brownfield detection

| What you write | What the coding agent does |
|---|---|
| "EXISTING REST API" | Generates FunctionTool wrapper, not new service |
| "DO NOT create new" | Skips infrastructure generation |
| "EXISTING database" | Uses existing connection config, doesn't generate new DB |
| "Use the existing" | References existing files (symlinks or imports) |
| "MUST NOT modify" | Preserves existing code, generates alongside it |

### Common mistakes

| Mistake | Why it's a problem | Better approach |
|---|---|---|
| "uses BigQuery" (no workload type) | Blueprint Advisor can't distinguish `execute_query` (analytical) from `execute_sql` (transactional) | "BigQuery (analytical queries, read-only)" |
| "body shop API" (no ownership) | Blueprint Advisor doesn't know if it's MCP or A2A | "body shop — they operate their own API" |
| "process the claim" (vague workflow) | Blueprint Advisor can't determine ordering or parallelism | Break into explicit steps with ordering words |
| Data source in Data Sources section only | Tool assigned to wrong agent (no co-occurrence) | Mention the data source IN the workflow step where it's used |
| "extract and save to Cloud SQL" in one step | Write tool assigned to leaf agent instead of coordinator | Split: "extract details" (leaf) then "save claim record" (coordinator step) |
| One spec for multiple apps | Too many concerns, confused tool assignments | One spec per application |

---

## 4a. Capturing Business Logic in the Spec

If you want the coding agent to generate business logic — not just scaffolding — add these four sections to your spec. When present, the coding agent generates 90-95% of the code. When omitted, you write business logic manually (~55 additional hours per use case).

### Business Rules

For each decision point in your workflow, write the rules:

```markdown
### Severity Classification

**Inputs:**
- damage_estimate (float) — from extract_details output
- injuries_reported (boolean) — from extract_details output
- fraud_score (float) — from fraud_scoring output

**Rules (evaluated in order):**
1. IF damage_estimate > 25000 OR injuries_reported THEN level=high, routing=adjuster_review
2. IF fraud_score > 0.7 THEN level=high, routing=adjuster_review
3. IF damage_estimate > 10000 THEN level=medium, routing=auto_approve
4. OTHERWISE level=low, routing=auto_approve

**Edge cases:**
- WHEN damage_estimate is missing THEN level=high, reason="missing data"
- WHEN fraud_score unavailable (timeout) THEN proceed without it, flag for manual review

**Validation:**
- damage_estimate must be >= 0
- fraud_score must be between 0.0 and 1.0
```

The Blueprint Advisor converts this into a `business_rules:` block in the blueprint. The coding agent generates working `classify_severity()` with all conditions, edge cases, and validation — not a stub.

### Transformation Rules

For each data transformation, write the mapping:

```markdown
### Claim Summary

**Input:** Enrichment results (weather, police, fraud, coverage)
**Output:** ClaimSummary

**Mapping:**
- summary.total_damage = body_shop_estimate + rental_cost
- summary.risk_score = (fraud_score × 0.6) + (severity_numeric × 0.4)
- summary.weather_factor = IF conditions IN ["heavy rain","ice","fog"] THEN "adverse" ELSE "normal"
```

### Error Handling

For each external dependency, write the fallback:

```markdown
### Body Shop A2A Agent
- Timeout (> 30s): Use cached average estimate. Flag for manual review.
- Failure: Skip enrichment. Set repair_estimate = null. Route to adjuster.
- Retry policy: 2 retries, exponential backoff (1s, 3s).
```

### Acceptance Criteria

For each workflow step, write GIVEN/WHEN/THEN assertions. These auto-generate your evalsets:

```markdown
### Policy Verification
- GIVEN policyholder "P-12345" with active coverage
  WHEN verify_policy runs
  THEN output contains policy_status=active AND coverage_type=comprehensive

- GIVEN policyholder "P-99999" with expired coverage
  WHEN verify_policy runs
  THEN routing changes to adjuster_review
```

The Blueprint Advisor converts these into starter golden dataset entries and pre-populated evalsets in `tests/evalsets/`. Your acceptance criteria become your automated evaluation — no separate test-writing step.

---

## 4b. EvalOps — Your Evaluation Workflow

> For the full EvalOps architecture (3-layer lifecycle, golden dataset lifecycle, meta-evaluation), see the Architecture Document (Layer 4 section).

> **Golden dataset quality gate:** Your pre-commit hook enforces minimum quality: ≥10 entries per agent, ≥3 edge cases, ≥1 negative test, 100% agent coverage. If your golden dataset doesn't meet these thresholds, the commit is blocked. The entries generated from your acceptance criteria are a starting point — you need to add edge cases and negative tests during development.

AgentCatalyst generates a complete evaluation lifecycle. You don't need to set this up — the `company-cicd` and `company-observability` skills generate everything.

### What gets generated for you

| Generated file | What it does | When it runs |
|---|---|---|
| `tests/eval_inner_loop.py` | Pre-commit hook — runs 5-10 evalsets locally via Vertex AI Evaluation SDK. Blocks commit if any metric drops >10%. | Every `git commit` |
| `.pre-commit-config.yaml` | Wires the inner loop evaluator as a pre-commit hook | Automatic |
| `tests/baseline_scores.json` | Baseline scores to compare against | Updated after each successful deployment |
| `observability/adk-tracing-config.py` | ADK tracing instrumentation — captures LLM calls, tool calls, loop iterations | Every agent run (local + deployed) |
| `observability/phoenix-config.py` | Arize Phoenix config — traces visible at `localhost:6006` during local dev | Local development |
| `golden-dataset/golden-v1.json` | Starter golden dataset from your acceptance criteria | Blueprint Advisor generates |
| `harness-pipeline.yaml` | 3-phase pipeline: Arize eval → AutoSxS comparison → HITL triage | Every PR merge |

### Your daily workflow with EvalOps

```
Edit code or prompts
  ↓
git commit
  ↓
Pre-commit hook runs inner loop (< 60 seconds)
  ├─ Pass → commit proceeds
  └─ Fail → "Groundedness dropped 18%. Review prompt changes."
  ↓
Push + PR merge
  ↓
Harness pipeline:
  Phase A: Arize eval (pass/fail gates)
  Phase B: AutoSxS vs baseline (edge case detection)
  Phase C: Human triage (reviewers approve/reject flagged cases)
  ↓
Production with Arize monitoring
  ↓
Drift detected? → Failing cases sampled → Human annotates
  → Golden dataset updated → Next deployment tested against real failures
```

### Debugging with Phoenix traces

When an evaluation fails, open Phoenix at `localhost:6006` to see the full trace:

```
fnol_coordinator (2.3s)
├── intake_pipeline (0.8s)
│   ├── verify_policy (0.5s)
│   │   └── BigQuery execute_query (0.3s) ← see actual SQL
│   └── extract_details (0.3s)
│       └── LLM call: input="caller said..." output="structured={...}"
├── enrichment_fan_out (1.1s)
│   ├── weather_check (0.4s)
│   ├── police_report (0.8s) ← A2A call, full request/response
│   └── fraud_scoring (0.2s) ← FunctionTool, see input/output
└── claim_summary_loop (0.4s)
    ├── iteration 1: quality=0.72 → retry
    └── iteration 2: quality=0.91 → exit ✓
```

This shows you exactly which agent failed, which tool returned bad data, and whether a loop converged — instead of just seeing a pass/fail score.

---

## 5. Understanding the app-blueprint.md

> **If the Blueprint Advisor is unavailable:** You can author `app-blueprint.md` manually using the template schema below and the FNOL example in the Architecture Document (Appendix A.10) as a template. The `/catalyst.generate` command only needs the `app-blueprint.md` file — it does not require the MCP Server. You lose the AI-guided recommendation but are not blocked from generating code.

> **How the blueprint is created:** Your coding agent calls `blueprint_start(spec, plan)` on the Blueprint Advisor MCP Server, which returns a task ID immediately. The background pipeline runs the Blueprint Advisor LlmAgent internally (RAG search + LLM reasoning + company system prompt) and stores the result when complete. Your coding agent polls `blueprint_status(taskId)` for progress and retrieves the result via `blueprint_result(taskId)`. After reviewing and editing, your coding agent calls `validate_composition(pattern_tree)` to check your edits, and `assemble_blueprint(selections, spec, plan)` to finalize the blueprint. All calls happen via MCP protocol — your coding agent never accesses Vertex AI Search or the LlmAgent directly. See the Architecture Document for the full MCP Server tool table.

### Agentic blueprint — key fields

```yaml
agents:
  - name: intake_pipeline     # Becomes: app/sub_agents/intake_pipeline.py
    type: SequentialAgent      # ADK class
    steps: [verify, extract]   # Execution order

tools:
  mcp_servers:
    - name: bigquery-policy    # Becomes: app/mcp_connections/bigquery_policy.py
      assigned_to: verify      # Wired to this agent's tools list
```

**The `assigned_to` field is critical** — it determines which agent gets which tool.

### Microservice blueprint — key fields

```yaml
backend:
  endpoints:
    - method: POST
      path: /api/greetings     # Becomes: GreetingController.createGreeting()
      handler: createGreeting

  entities:
    - name: Greeting           # Becomes: Greeting.java (entity) + GreetingRepository.java
      table: GREETINGS
```

### Brownfield signals in the blueprint

```yaml
infrastructure:
  terraform:
    action: SKIP              # Don't generate Terraform
  cicd:
    action: SKIP              # Don't generate CI/CD
database:
  config_source: boilerplate/backend/src/main/resources/application.yml  # Use EXISTING config
```

### Diagrams in the blueprint

The Blueprint Advisor generates three Mermaid diagrams inline in the markdown (§14 Sequence Diagrams section). These are not separate files — they're part of the same `app-blueprint.md` you already review.

| Diagram | What you see | What to check |
|---|---|---|
| **Component** | Agent tree with boxes for each agent, connected to their tools (MCP servers as cylinders, A2A as hexagons, FunctionTools as parallelograms) | "Does each agent connect to the right tools? Are any tools orphaned or assigned to the wrong agent?" |
| **Sequence** | Step-by-step message flow showing what happens at runtime — Sequential phases in order, Parallel branches side-by-side, Loop iterations, HITL routing | "Does the flow match my spec's Workflow section? Are the parallel branches correct? Does HITL route on the right condition?" |
| **Infrastructure** | GCP services inside VPC-SC boundary, external partners outside, CI/CD pipeline connections | "Are all the services I need inside the perimeter? Are external partners shown correctly?" |

**How to view them:** Open `app-blueprint.md` in VSCode. If you have a Mermaid preview extension installed (most setups do), the diagrams render automatically in the preview pane. You can review the markdown tables on the left and see the architecture visually on the right.

**How to edit them:** The diagrams are Mermaid text — you can edit agent names, add notes, adjust layout. If you change the `agents:` or `tools:` sections and re-run `/catalyst.blueprint`, the diagrams regenerate to match.

**How to export them:** If you need PNG/SVG for documentation or a presentation, your CI pipeline can render them automatically. Or locally: `npx -p @mermaid-js/mermaid-cli mmdc -i diagram.mmd -o diagram.png`.

**Pro tip:** During PR review, GitHub and GitLab render Mermaid blocks natively. Your team sees the architecture diagram right in the PR — no extra steps needed.

---

## 6. Re-generating — Iterating on the Design

You can change the blueprint and re-run `/catalyst.generate` as many times as needed.

### How to re-generate safely

```bash
# Re-generate to a NEW directory, then diff
/catalyst.generate --output ./my-app-v2
diff -r my-app my-app-v2
```

Or use git:

```bash
git add . && git commit -m "before re-generate"
/catalyst.generate
git diff   # See exactly what changed
```

### What happens to custom code

Files marked `<<< ENGINEER MUST WRITE >>>` (system prompts) or FunctionTool implementations with first-draft business logic may contain your refinements. If you've already reviewed and refined them and then re-generate, the generated version will overwrite your changes. **Always commit before re-generating.**

---

## 7. Writing Tests for Generated Code

### Agentic: Agent evaluation datasets

For agents, create evaluation datasets that test the agent's tool-calling behavior:

```json
// tests/evalsets/fnol-basic.json
[
  {
    "test_id": "fnol-001-policy-verification",
    "input": "I was in a car accident on I-85. My policy number is P-12345.",
    "expected_tool_calls": ["bigquery-policy.execute_query"],
    "expected_agent_sequence": ["fnol_coordinator", "intake_pipeline", "verify_policy"],
    "expected_output_contains": ["policy verified", "active coverage"],
    "max_latency_ms": 3000
  },
  {
    "test_id": "fnol-002-high-severity-routing",
    "input": "The damage is about $30,000 and there were injuries.",
    "expected_tool_calls": ["severity_classifier"],
    "expected_output_contains": ["high severity"],
    "expected_routing": "adjuster_review",
    "max_latency_ms": 2000
  }
]
```

These evalsets are run by the **Harness pipeline against the deployed agent via Arize** — not locally. You commit them with your code; the pipeline takes care of execution.

Why not run them locally? Two reasons:
1. **No preview API dependency** — Arize is GA SaaS, available everywhere. Agent Evaluation Service (preview) might not be enabled in your project.
2. **Real environment validation** — local evaluation against mocked agents can pass while real deployment fails. Arize evaluates the actually deployed agent.

For local fast-feedback testing, write **unit tests with mocks** (covered in the next subsection).

### Microservices: Spring Boot + Angular tests

Generated code includes test stubs. Here's how to flesh them out:

**Spring Boot controller test:**

```java
// backend/src/test/java/com/company/helloworld/controller/GreetingControllerTest.java
@WebMvcTest(GreetingController.class)
class GreetingControllerTest {

    @Autowired private MockMvc mockMvc;
    @MockBean private GreetingService greetingService;

    @Test
    void listGreetings_returnsAll() throws Exception {
        when(greetingService.findAll()).thenReturn(List.of(
            new GreetingResponse(1L, "Alice", "Hello", Timestamp.valueOf("2026-01-01 00:00:00"))
        ));

        mockMvc.perform(get("/api/greetings"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$[0].name").value("Alice"));
    }

    @Test
    void createGreeting_returnsCreated() throws Exception {
        mockMvc.perform(post("/api/greetings")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"name\":\"Bob\",\"message\":\"Hi\"}"))
            .andExpect(status().isOk());
    }
}
```

**Angular service test:**

```typescript
// frontend/src/app/services/greeting.service.spec.ts
describe('GreetingService', () => {
  let service: GreetingService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [HttpClientTestingModule] });
    service = TestBed.inject(GreetingService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('should fetch all greetings', () => {
    service.findAll().subscribe(greetings => {
      expect(greetings.length).toBe(1);
      expect(greetings[0].name).toBe('Alice');
    });
    const req = httpMock.expectOne('/api/greetings');
    req.flush([{ id: 1, name: 'Alice', message: 'Hello' }]);
  });
});
```

### Tips for effective tests

| Archetype | What to test | What NOT to test |
|---|---|---|
| **Agentic** | Tool call sequences, routing decisions, exit conditions, FunctionTool logic | ADK framework internals (Google tests those) |
| **Microservice** | Controller request/response, service business logic, repository queries, API contract compliance | Spring Boot framework internals |
| **Both** | Integration with existing infrastructure (Oracle, BigQuery, MCP) | Generated boilerplate (trust the skills) |

---

## 8. Reading Blueprint Advisor Confidence Scores

The Blueprint Advisor returns each recommendation with a confidence score. Confidence comes from how strongly your spec matched the catalog — not from the LLM's reasoning. Understanding the score helps you decide what to trust and what to question.

### What confidence means

| Tier | Score range | What it means | What you should do |
|---|---|---|---|
| **High** | ≥ 0.85 with clear gap to next result | The catalog has a clear winner — search returned one obvious match | Trust it. Verify `assigned_to` is on the right agent and move on. |
| **Medium** | 0.65–0.85, or top score is high but next is close | Multiple candidates matched. The Blueprint Advisor picked the best, but alternatives exist. | Check the `alternatives:` field in the blueprint. Pick the one that matches your intent. |
| **Low** | < 0.65 | Search couldn't find a confident match. Either the spec is ambiguous or the catalog doesn't have what you need. | Don't accept the recommendation. Either rewrite the spec to be more specific, or contact platform engineering if you think a tool is missing from the registry. |

### Example: Medium confidence with alternatives

```yaml
tools:
  mcp_servers:
    - name: bigquery-policy
      assigned_to: verify_policy
      confidence: 0.78          # Medium — alternatives present
      alternatives:
        - name: bigquery-claims-history
          score: 0.71
          reason: "Also matches 'BigQuery analytical' but in claims domain"
```

The Blueprint Advisor picked `bigquery-policy` because your spec mentioned policy data. But it's telling you `bigquery-claims-history` is a close second — if you actually need claims history data, switch the assignment.

### Example: Low confidence flag

```yaml
tools:
  mcp_servers:
    - name: TBD
      assigned_to: verify_policy
      requires_review: true
      confidence: 0.52
      notes: "Spec mentions 'data warehouse' but no specific system. 
              Please specify BigQuery (analytical) or Cloud SQL (transactional) 
              and re-run /catalyst.blueprint."
```

When you see `requires_review: true`, the Blueprint Advisor is telling you it can't make a confident recommendation. Don't run `/catalyst.generate` — fix the spec first.

---

## 9. When the Blueprint Advisor Gets It Wrong

Even with good specs, the Blueprint Advisor sometimes misses. Here are the most common failure modes and how to diagnose them.

### Failure mode 1: Tool assigned to wrong agent

**Symptom:** Generated code has `cloud-sql-claims` connected to `extract_details`, but `extract_details` doesn't actually write to Cloud SQL — the coordinator does.

**Why it happened:** Your spec said *"extract details and save to Cloud SQL"* in one sentence. The Blueprint Advisor saw co-occurrence between "extract" and "Cloud SQL" and assigned them together.

**How to fix:**
1. In the blueprint, change `assigned_to: extract_details` to `assigned_to: fnol_coordinator`
2. To prevent this recurring, rewrite the spec to separate the actions: *"Extract incident details from the caller's description. The coordinator records the claim in our Cloud SQL claims database."*

### Failure mode 2: Search returns alternatives instead of a clear winner

**Symptom:** Multiple `alternatives:` fields in the blueprint. The Blueprint Advisor isn't sure which tool you wanted.

**Why it happened:** Your spec is ambiguous. Either you used generic language ("data warehouse") or your data sources overlap (multiple BigQuery datasets in the registry).

**How to fix:**
1. Pick the right alternative manually in the blueprint, or
2. Rewrite the spec to be specific. "Query BigQuery" is ambiguous if there are 3 BigQuery datasets in the registry. "Query the policy data warehouse in BigQuery" is unambiguous.

### Failure mode 3: A tool you need isn't in the recommendation

**Symptom:** Your spec mentions a system, but no MCP server or A2A agent for it appears in the blueprint.

**Why it happened:** Two possibilities:
- The tool isn't in the registry (catalog gap)
- The tool is in the registry but enrichment metadata doesn't match your spec language

**How to diagnose:**
1. Check `memory/approved-tools.md` to see if the tool exists
2. If it exists but wasn't found, the issue is enrichment metadata. Add the tool manually to the blueprint and report the search miss to platform engineering.
3. If it doesn't exist, this is a registry gap. Submit a request via platform engineering JIRA.

### Failure mode 4: Pattern composition that doesn't make architectural sense

**Symptom:** Generated blueprint composes patterns that shouldn't be composed (e.g., LoopAgent with HITL sub-agent).

**Why it happened:** Your spec described both iteration and human approval, and the Blueprint Advisor combined them naively. The pattern composition validator should have caught this — if it didn't, it's a validator gap.

**How to fix:**
1. Re-architect the blueprint so iteration happens before human approval, not within it
2. Re-run `/catalyst.generate` — the validator should now pass
3. Report the missed composition rule to EA

### Failure mode 5: Brownfield signals ignored

**Symptom:** You wrote "EXISTING database — DO NOT create new" but the blueprint still includes Terraform for a new database.

**Why it happened:** The brownfield signal was buried or contradicted elsewhere in the spec.

**How to fix:**
1. Set `infrastructure.terraform.action: SKIP` manually in the blueprint
2. Strengthen the spec: put "EXISTING" / "DO NOT create new" in BOTH the Dependencies section AND the Infrastructure Requirements section

### When to fix the blueprint vs rewrite the spec

| Situation | Action |
|---|---|
| One or two field-level mistakes (wrong `assigned_to`) | Fix the blueprint directly. Cheaper than re-running. |
| Multiple field-level mistakes, but pattern is correct | Fix the blueprint. Note the pattern in your team's spec-writing guide. |
| Wrong pattern selected (Sequential when you meant Parallel) | Rewrite the spec with clearer ordering language, re-run /catalyst.blueprint |
| Multiple `requires_review: true` fields | Rewrite the spec entirely. The Blueprint Advisor is telling you the spec is too ambiguous. |
| Tool you need isn't in the registry | Add manually to blueprint + submit JIRA request to platform engineering |

### When to escalate to platform engineering

| Issue | How to escalate |
|---|---|
| Tool missing from registry | Platform engineering JIRA: include tool name, vendor, business case, contact info |
| Search consistently returns wrong tool for your data source | Platform engineering JIRA: include 3+ examples of spec language → wrong recommendation |
| Pattern composition that should have been blocked | EA office hours: bring the blueprint and explain why the composition is invalid |
| Acceptance metrics on dashboard show your LOB at < 60% | Schedule spec quality review with EA |

---

## 10. Spec Quality Self-Check

Run this 10-question checklist before `/catalyst.blueprint`. A spec that passes all 10 gets ~95% Blueprint Advisor accuracy. A spec that fails several gets ~60%.

### The checklist

| # | Question | Why it matters |
|---|---|---|
| 1 | Does each workflow step start with an ordering word ("First," "Then," "Simultaneously," "Refine until," "If")? | These trigger pattern selection. Missing them produces wrong topology. |
| 2 | Is each data source mentioned in a workflow step (not only in the Data Sources section)? | Co-occurrence drives tool-to-agent assignment. No co-occurrence = wrong assignment. |
| 3 | Does each external integration include "they operate" or "we operate" language? | Determines MCP vs A2A vs FunctionTool. Ambiguous ownership produces wrong connection type. |
| 4 | Does each database/data source specify workload type (analytical, transactional, retrieval)? | Determines which specific tool on the MCP server is selected. |
| 5 | Are FunctionTool implementations explicitly marked "our proprietary" or "internal model"? | Tells the Blueprint Advisor not to search for these — they're implementations generated from your spec rules. |
| 6 | If brownfield: are "EXISTING" / "DO NOT create" signals in BOTH Dependencies and Infrastructure sections? | Brownfield signals must be unambiguous to skip infrastructure generation. |
| 7 | Is the Workflow section a sequence of explicit steps (not a wishlist or paragraph)? | Wishlists can't be parsed for ordering. |
| 8 | Are write actions ("create record," "update status") attributed to the coordinator, not extraction or enrichment steps? | Write tools assigned at coordinator scope are usually correct. Writes attributed to leaf agents are usually wrong. |
| 9 | If two systems serve similar purposes (BigQuery + Cloud SQL), is each one's purpose disambiguated? | Two analytical systems mentioned in one step produces ambiguous matches. |
| 10 | Is the spec for a single application (not multiple applications combined)? | Multi-app specs produce confused tool assignments. |

### Example — running the checklist on a real spec

**Spec text:**

> "We need an agent for FNOL. It checks coverage and gets repair estimates."

| # | Pass/Fail | Why |
|---|---|---|
| 1 | ❌ Fail | No ordering words. Will not produce a clear pattern. |
| 2 | ❌ Fail | No data sources mentioned in workflow. |
| 3 | ❌ Fail | No ownership signals. |
| 4 | ❌ Fail | No workload types. |
| 5 | ❌ Fail | No proprietary callouts. |
| 6 | N/A | Greenfield. |
| 7 | ❌ Fail | One paragraph, not steps. |
| 8 | ❌ Fail | No write actions specified. |
| 9 | N/A | No similar systems. |
| 10 | ✓ Pass | Single app. |

**Score: 1/10. The Blueprint Advisor will struggle.**

**Improved spec:**

> "## Workflow
> 1. First, verify coverage by querying our BigQuery policy data warehouse (analytical, read-only).
> 2. Then, extract incident details from the caller's description.
> 3. Simultaneously enrich with: weather data, police report (municipal — they operate it), repair estimates (body shop network — they operate their own quoting service).
> 4. Generate a claim summary, validate against our quality rubric, refine until quality > 0.85.
> 5. The coordinator records the claim in our Cloud SQL claims database (transactional, read-write).
> 6. If severity is high, route to a human adjuster.
> 
> ## Internal Capabilities
> - Our proprietary fraud detection model
> - Our proprietary severity classifier"

**Score: 10/10. The Blueprint Advisor will produce high-confidence recommendations.**

---

## 11. Reporting Issues to Platform Engineering

> The Platform Engineering team uses the acceptance telemetry pipeline (see Operations Runbook, Section 3) to track Blueprint Advisor quality. Your issue reports supplement this automated telemetry.

The Blueprint Advisor improves over time based on developer feedback. Reporting issues isn't a complaint — it's how the system gets smarter.

### How to report a missing tool

**When:** You wrote a spec that mentioned a system, but no tool for it appeared in the recommendation.

**Where:** Platform engineering JIRA — `AGENTCATALYST-TOOLS` queue.

**What to include:**
- Tool name and vendor
- Endpoint (if known)
- Business case (which use case needs it, why existing tools don't suffice)
- Owner contact (vendor TAM or internal team that operates it)

**Timeline:** Tool registration takes 1–2 weeks. Tool starts in `preview` state for 30 days, then `active`.

### How to report a wrong pattern recommendation

**When:** Your spec was clear, but the Blueprint Advisor picked the wrong pattern.

**Where:** EA office hours OR EA `AGENTCATALYST-PATTERNS` queue.

**What to include:**
- The spec text (especially the Workflow section)
- The recommended pattern
- The pattern you expected
- Why the recommendation is wrong (which signal phrases the Blueprint Advisor missed or misinterpreted)

**Timeline:** EA reviews monthly. System prompt or pattern catalog updates ship in the next quarterly release.

### How to report search quality issues

**When:** The Blueprint Advisor consistently picks the wrong tool for the same kind of spec language across multiple use cases.

**Where:** Platform engineering JIRA — `AGENTCATALYST-SEARCH` queue.

**What to include:**
- 3+ examples of spec language that produced wrong tool recommendations
- The tool you expected
- The tool that was recommended

**Timeline:** Platform engineering reviews telemetry weekly. Enrichment metadata or system prompt updates ship within 2 weeks.

### What platform engineering does with your reports

| Report type | Action taken |
|---|---|
| Missing tool | Tool added to registry with full enrichment metadata |
| Wrong pattern | Pattern catalog metadata updated, system prompt heuristics revised |
| Search quality issue | Enrichment metadata for affected tools updated, regression suite expanded with your examples |

Your reports become test cases in the regression suite — preventing future regressions for everyone.

---

## 12. Deployment Rules — What NOT to Do

> These rules are enforced by `constitution.md` in your preset. The coding agent reads constitution.md before generating code and will refuse to generate deployment commands or direct infrastructure provisioning. See the Architecture Document (Layer 3) for the full list of non-negotiable rules.

> See the Architecture Document for the full CI/CD architecture (Layer 4 — Jenkins infrastructure plane + Harness application plane with 3-phase EvalOps).

| ❌ Never do this | ✅ Do this instead |
|---|---|
| Deploy directly from your machine | Commit → PR → Jenkins → Harness |
| Run `agents-cli deploy` (if installed) | Company-cicd skill generates pipeline files instead |
| Run `agents-cli eval` or `agents-cli simulate` | Write evalsets locally; Harness runs them via Arize against the deployed agent |
| Generate Cloud Build config | Company uses Jenkins |
| Provision GCP/AWS resources manually | Jenkins runs Terraform after PR merge |

The `company-cicd` skill explicitly tells the coding agent: "Generate pipeline files. Do not deploy directly. Do not call preview GCP services." Three override layers (skill + GEMINI.md + command) reinforce this.

### How evaluation works in production

Local testing (your machine):
- `pytest tests/unit/` — unit tests with mocks (fast feedback)
- Don't try to run end-to-end evaluation locally — it requires the agent to be deployed

CI/CD (after PR merge):
- Harness deploys agent to non-prod
- Harness runs your evalsets via Arize against the non-prod agent
- Quality gates check: pass rate ≥ 95%, p95 latency ≤ 3s, hallucination ≤ 0.15
- If gates pass, the same flow runs in pre-prod, then prod canary

This pattern avoids any dependency on Agent Evaluation Service or Agent Simulation Service (both pre-GA preview services). AgentCatalyst is deployable to any GCP project — including locked-down environments where preview APIs are not enabled.

Your evalsets in `tests/evalsets/` are the input. Harness + Arize handle the rest.

---

## 13. A Concrete Deployment Scenario — FNOL Agent Merge to Production

To make the CI/CD model concrete, here's exactly what happens when you merge a PR for an FNOL agent change. Two distinct pipelines run in sequence — Jenkins for infrastructure, Harness for application. Understanding both helps you debug failures and write better evalsets.

```
1. Developer merges PR to main branch
        │
        ▼
2. JENKINS pipeline triggers (agent-infra-plan-apply-v3)
        │
        ├─ Checkout code, including deployment/terraform/
        │
        ├─ Terraform init
        │   └─ Loads state from GCS backend
        │
        ├─ Terraform plan
        │   └─ Generates plan.json showing what will change
        │
        ├─ OPA policy check
        │   ├─ "All Cloud SQL must use CMEK" ✓
        │   ├─ "All buckets must be private" ✓
        │   ├─ "Agent must run in VPC-SC perimeter" ✓
        │   └─ All policies pass
        │
        ├─ Terraform apply
        │   └─ Updates infrastructure (e.g., adds new MCP server config,
        │      updates Vertex AI Search data store, rotates secrets)
        │
        ├─ Infrastructure health check
        │   ├─ Cloud SQL responding ✓
        │   ├─ Vertex AI Search index up to date ✓
        │   ├─ Model Armor config valid ✓
        │   └─ All healthy
        │
        └─ Trigger Harness pipeline
            └─ POST to Harness API with build context
                │
                ▼
3. HARNESS pipeline triggers (agent-deploy-canary-v4)
        │
        ├─ Build container image
        │   ├─ Docker build with new agent code
        │   └─ Push to Artifact Registry as agents/fnol-coordinator:abc123
        │
        ├─ Deploy to Non-Prod
        │   ├─ gcloud agents deploy fnol-coordinator --version abc123 ...
        │   └─ Cloud Run routes 100% non-prod traffic to new revision
        │
        ├─ Arize evaluation against Non-Prod
        │   ├─ Run all evalsets in tests/evalsets/
        │   ├─ Pass rate: 97% ✓ (threshold 95%)
        │   ├─ p95 latency: 2.1s ✓ (threshold 3s)
        │   ├─ Hallucination score: 0.08 ✓ (threshold 0.15)
        │   └─ All gates pass — proceed
        │
        ├─ Approval gate (manual)
        │   └─ Tech lead approves promotion to Pre-Prod
        │
        ├─ Deploy to Pre-Prod (canary 10%)
        │   ├─ 10% of pre-prod traffic to new version
        │   ├─ Monitor for 30 minutes
        │   │   ├─ Dynatrace: p95 latency 2.3s ✓
        │   │   ├─ Dynatrace: error rate 0.02% ✓
        │   │   └─ Arize: hallucination drift +0.01 ✓
        │   └─ Promote to 100% pre-prod
        │
        ├─ Arize evaluation against Pre-Prod
        │   └─ All gates pass
        │
        ├─ Deploy to Prod (progressive)
        │   ├─ Canary 10% (30 min monitoring)
        │   ├─ Canary 25% (30 min monitoring)
        │   ├─ Canary 50% (30 min monitoring)
        │   └─ Full rollout 100%
        │
        └─ Deployment complete
            └─ Slack notification + Splunk audit log entry
```

### What happens when something fails

If anything fails — Terraform plan rejected by OPA, Arize gates fail, SLOs violated during canary — Harness automatically rolls back to the previous agent version. Jenkins doesn't roll back infrastructure (Terraform state needs careful manual handling), but the failed Terraform apply is visible in Jenkins for platform engineering to address.

### Why this two-plane model matters

The reason AgentCatalyst forbids direct deployment from your workstation and forces this two-plane model is governance. Each plane enforces a specific control:

| Governance concern | How it's enforced |
|---|---|
| Infrastructure follows company standards | Jenkins runs OPA policy checks before Terraform apply |
| All changes are traceable | Every deployment has Jenkins run ID + Harness execution ID logged in Splunk |
| Production deployments require approval | Harness manual approval gate before pre-prod promotion |
| Quality gates protect production | Arize evaluation must pass before each environment promotion |
| Bad deployments don't take down production | Canary deployment + automatic SLO-based rollback in Harness |
| No one can bypass the pipeline | Direct deployment is forbidden by three-layer skill override; CI/CD is the only path |

If you bypassed the pipeline and deployed directly, none of this happens. The agent would go straight to 100% traffic with no policy checks, no quality gates, no canary, no rollback, no audit trail. That's the failure mode AgentCatalyst prevents.

### Jenkins vs Harness — what each one is for

| Question | Jenkins | Harness |
|---|---|---|
| What does it deploy? | Infrastructure (cloud resources) | Application (agent code) |
| What tool does it run? | Terraform | Container deployment + traffic shifting |
| How often does it run? | Infrequently (weeks) | Frequently (multiple times per day) |
| Rollback strategy | Re-run Terraform (manual, careful) | Automatic traffic shift to previous version |
| Pipeline ownership | Platform engineering | Your team (with platform-provided template) |
| Unit of change | Terraform plan | Container image |
| Gate types | OPA policy checks | Arize quality gates + SLO validation |

Both are essential. Jenkins ensures the agent's environment is correct. Harness ensures the agent's deployment is safe. Together they take your agent from `git push` to production at enterprise scale.

---

## 14. Troubleshooting

> For platform-level failure modes and escalation procedures, see the Operations Runbook, Section 6 (Failure Modes) and Section 9 (MCP Server Operations). If the Blueprint Advisor MCP Server is unreachable or returning errors, contact Platform Engineering per the escalation matrix in the Operations Runbook.

| Problem | Cause | Fix |
|---|---|---|
| `/catalyst.blueprint` returns error | Blueprint Advisor API unreachable | Check `CATALYST_BLUEPRINT_API` env var |
| Blueprint task stuck in "working" for >5 min | Pipeline slow or Cloud Run Jobs quota exceeded | Check the Chat pane for the last progress message. If stuck on "Searching pattern catalog," the Vertex AI Search may be slow. If stuck on "Reasoning," the LLM call is running long. Wait up to 10 min for complex specs (10+ integrations). If no progress after 10 min, cancel and re-run with a simpler spec. Report to Platform Engineering if persistent. |
| `/catalyst.assess` returns error | Governance Guardian MCP Server unreachable | Check network connectivity. The Governance Guardian uses the same OAuth as Blueprint Advisor. If persistent, proceed without assessment: `/catalyst.generate` will warn but allow `skip`. |
| Assessment finds showstoppers you disagree with | EA standards may not match your use case | Contact the EA office to discuss. If the standard doesn't apply, request an exception via the governance exception process. You cannot bypass showstoppers — they must be resolved or exempted by EA. |
| `/catalyst.generate` blocked by governance gate | Showstopper findings still present | Run `/catalyst.assess` to see current findings. Fix showstoppers and re-assess. Only showstoppers block generation — non-showstoppers are recorded as tech debt. |
| MCP Server returns 401 Unauthorized | OAuth token expired or MFA timed out | Close and reopen VSCode to trigger a fresh SSO login (Entra ID). If persistent, check with IT that your Entra ID account is active. The coding agent refreshes tokens automatically; a 401 usually means the refresh token also expired (>24 hours since last login). |
| Blueprint validation fails | Schema error | Common: missing `assigned_to`, unpinned version, invalid type |
| Skill provenance check fails | Skill updated since blueprint generated | Update `version:` in blueprint |
| Skills not visible | Not installed | Run `gemini skills install github.com/company/agentcatalyst-skills --scope user` |
| Coding agent tries to deploy directly | Default workflow overriding company rules | Verify skills installed, check GEMINI.md has override table |
| Brownfield generates new infrastructure | Spec missing "EXISTING" / "DO NOT create" signals | Add explicit brownfield language to spec (see Section 4) |
| Generated code doesn't compile | Skill version mismatch | Check ADK/Spring Boot version matches skill expectations |
| Oracle connection fails locally | Wrong JDBC URL or missing credentials | Check `application.yml` datasource config, ensure Oracle RDS is accessible from your machine |
| Blueprint Advisor consistently picks wrong tool for my data source | Tool registry enrichment metadata is incomplete or doesn't match your spec language | Submit feedback via platform engineering JIRA (`AGENTCATALYST-SEARCH` queue) with 3+ examples of your spec language → wrong recommendation. See Section 11. |
| Search returns alternatives instead of a clear winner (multiple `alternatives:` fields in blueprint) | Spec is ambiguous — multiple tools or patterns match equally well | Run the Spec Quality Self-Check (Section 10). Disambiguate the spec or pick the right alternative manually in the blueprint. |
| Generated code fails because tool no longer exists | Tool was deprecated since the blueprint was generated | Check tool deprecation list. Run `catalyst migrate` if available, or update blueprint manually to use the replacement tool. Re-run `/catalyst.generate`. |
| Pattern composition validator rejects YAML | YAML composes patterns that aren't compatible (e.g., LoopAgent + HITL sub-agent) | Read the validator error — it specifies which composition rule was violated. Either restructure the YAML or rewrite the spec to use compatible patterns. |
| YAML has `requires_review: true` fields | Blueprint Advisor returned low-confidence results (< 0.65) | Don't run `/catalyst.generate`. Read the `notes:` field for what's ambiguous. Rewrite the spec to be more specific and re-run `/catalyst.blueprint`. |

### Getting help

| Channel | When |
|---|---|
| `#agentcatalyst` Slack | General questions, peer help |
| Platform Engineering JIRA — `AGENTCATALYST-TOOLS` | Missing tool requests |
| Platform Engineering JIRA — `AGENTCATALYST-SEARCH` | Search quality issues, wrong recommendations |
| Platform Engineering JIRA — `AGENTCATALYST-PATTERNS` | Wrong pattern selection |
| EA office hours | Pattern questions, spec reviews, architecture guidance, complex composition issues |

---

## 15. Reference — All Commands

| Command | What it does |
|---|---|
| `specify preset add agentcatalyst-agentic` | Install agentic preset |
| `specify preset add agentcatalyst-microservice` | Install microservice preset |
| `specify init --preset agentcatalyst-agentic` | Initialize project with preset |
| `/specify` | Present archetype-specific spec template |
| `/plan` | Present technical plan template |
| `/catalyst.blueprint` | Submit to Blueprint Advisor → YAML |
| `/catalyst.generate` | Generate code using skills |
| `/tasks` | Show generated vs engineer-implements breakdown |
| `gemini skills install <repo> --scope user` | Install skills globally |
| `/skills list` | Verify installed skills |

---

## 15. Preset File Map

Every file in the `.specify/` folder serves a specific purpose:

```
.specify/
├── preset.yml                    ← Manifest: archetype, templates, commands, settings
│
├── templates/
│   ├── spec-template.md          ← /specify loads this — archetype-specific sections
│   │                                with coaching prompts and examples
│   ├── plan-template.md          ← /plan loads this — technical questions
│   │                                mapping to markdown blueprint fields
│   └── tasks-template.md        ← /tasks loads this — generated vs
│                                    engineer-implements breakdown
│
├── commands/
│   ├── catalyst.blueprint.md    ← /catalyst.blueprint — instructions for
│   │                                the coding agent to call Blueprint
│   │                                Advisor API and save YAML
│   ├── catalyst.assess.md       ← /catalyst.assess — instructions for
│   │                                the coding agent to extract artifacts
│   │                                and call Governance Guardian API
│   └── catalyst.generate.md     ← /catalyst.generate — governance gate
│                                    + skill activation sequence with
│                                    CRITICAL override: DO NOT deploy directly
│
└── memory/
    ├── adk-reference.md          ← ADK class reference — loaded into
    │                                coding agent context during /specify
    ├── company-patterns.md       ← Company naming conventions, folder
    │                                structure, coding standards
    ├── approved-tools.md         ← Approved MCP servers + A2A agents
    │                                with endpoints and auth methods
    └── infra-standards.md        ← TF module registry, version pinning
                                     rules, CI/CD templates, security defaults
```

Complete preset source code is in **Appendix A of the Architecture Document** (`agentcatalyst-architecture.md`).

---

## 16. FAQ

**Q: Can I write the YAML manually?**
A: Yes. The coding agent doesn't care who produced the YAML. Write it by hand, copy from a teammate, or use any tool.

**Q: Can I use different coding agents for different steps?**
A: Yes. `/specify` in Copilot, `/catalyst.generate` in Claude Code — the preset files are the same.

**Q: What if my pattern doesn't have a ref impl (like the SPA pattern)?**
A: That's exactly the scenario in Section 3. Use AgentCatalyst to generate the application code on top of the existing IaC and boilerplate. The coding agent's skills teach it how to write correct Spring Boot / Angular / ADK code that plugs into the existing infrastructure.

**Q: Can I use AgentCatalyst for non-GCP infrastructure (AWS, Azure)?**
A: For the agentic archetype, GCP is required (Cloud Run is GCP-only for the agentic archetype). For microservice/pipeline/API archetypes, the application code is cloud-agnostic — only the company overlay skills (Terraform, CI/CD) are cloud-specific. The SPA brownfield example uses ECS Fargate (AWS).

**Q: Why not just use a project template (like Spring Initializr)?**
A: Templates give you a blank starter. AgentCatalyst gives you a starter that's already wired to your specific database, your specific APIs, your specific infrastructure, following your company's specific patterns. The Blueprint Advisor reads your spec and generates a YAML that's custom to your use case — not a generic template.

**Q: Is the generated code production-ready?**
A: The boilerplate is production-ready — correct framework patterns, proper project structure, company-standard infrastructure. You add: business logic, system prompts (for agents), test data, and domain-specific validation. That's the 20%.

**Q: How does this work with existing IaC that uses AWS (not GCP)?**
A: The brownfield SPA example in Section 3 uses AWS (ECS Fargate + Oracle RDS). AgentCatalyst generates the application code — it doesn't care about the cloud provider for the infrastructure. The `infrastructure.terraform.action: SKIP` flag tells it to leave existing infrastructure untouched. The company overlay skills for CI/CD would reference Jenkins/Harness templates appropriate for AWS deployment.

---

## Related Documents

| Document | Audience | What it covers | When to consult |
|---|---|---|---|
| **AgentCatalyst GA Architecture Document** | Architects, tech leads | WHY — architectural decisions, Blueprint Advisor MCP Server design (3-tool architecture), preset-based archetype adaptation, 5-layer architecture, cost model, ROI | When you need to understand why something is designed the way it is |
| **This Developer Guide** | Developers | HOW — step-by-step walkthroughs (greenfield FNOL + brownfield microservice), spec writing, business logic capture, EvalOps workflow, troubleshooting | When you need to build something |
| **AgentCatalyst Operations Runbook** | Platform engineering | PROCEDURES — wire-level Vertex AI Search APIs, search quality regression suite, acceptance telemetry, catalog quality engineering, tool lifecycle management, failure modes, escalation matrix | When you need to debug platform issues or maintain the Blueprint Advisor |
| **Governance Guardian Architecture Extension** | Architects, EA office, developers | `/catalyst.assess` design, solution package schema, scorecard format, `recordTechDebt` gate, tech debt registry | When you need to understand the governance assessment flow or troubleshoot assessment findings |

### Key cross-references from this guide to the Architecture Document

| This guide section | Architecture doc section | Why you might need it |
|---|---|---|
| Section 2-3 (Walkthroughs) | End-to-end thread | Narrative context for what the walkthrough steps do |
| Section 4 (Writing Specs) | Layer 2 — 11 agentic patterns table | Full list of patterns and selection signals |
| Section 4a (Business Logic) | Layer 1 — spec template table | How each spec section impacts code generation |
| Section 4b (EvalOps) | Layer 4 — EvalOps lifecycle | Full 3-layer architecture + golden dataset lifecycle |
| Section 5 (YAML Blueprint) | Layer 2 — MCP Server tools | How the YAML is created (3 MCP tools) |
| Section 8 (Confidence Scores) | Layer 2 — Blueprint Advisor | How confidence is determined |
| Section 12 (Deployment Rules) | Layer 4 — Company CI/CD | Jenkins + Harness architecture |
| Section 13 (Deployment Scenario) | Architecture doc — FNOL walkthrough | Architectural context for deployment steps |

*The architecture document provides the WHY. This guide provides the HOW. The operations runbook provides the PROCEDURES for maintaining the platform.*
