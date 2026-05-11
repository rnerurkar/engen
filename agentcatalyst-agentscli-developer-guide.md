# AgentCatalyst — agents-cli GA-Only Developer Guide

**Practical guide for developers building agentic AI applications with AgentCatalyst**
*Uses agents-cli for scaffolding · GA-only runtime · agents-cli eval/simulate/deploy FORBIDDEN*
*Companion to: AgentCatalyst agents-cli Architecture Document · AgentCatalyst Operations Runbook*

> This guide covers the HOW — step-by-step walkthroughs, code examples, spec writing, troubleshooting. For architectural decisions (the WHY), see the Architecture Document. For operational procedures (platform maintenance), see the Operations Runbook.
>
> **Key difference from the GA Developer Guide:** This variant uses `agents-cli scaffold create` for project setup (gets 7 Google skills bundled for free) but `agents-cli eval`, `agents-cli simulate`, and `agents-cli deploy` are **FORBIDDEN**. All evaluation goes through pre-commit hooks + Harness 3-phase pipeline. All deployment goes through Jenkins + Harness CI/CD.

**Practical guide for developers building agentic AI applications with AgentCatalyst**
*Uses agents-cli for scaffolding · GA-only runtime · agents-cli eval/simulate/deploy FORBIDDEN*
*Companion to: AgentCatalyst agents-cli Architecture Document · AgentCatalyst Operations Runbook*

> This guide covers the HOW — step-by-step walkthroughs, code examples, spec writing, troubleshooting. For architectural decisions (the WHY), see the Architecture Document. For operational procedures (platform maintenance), see the Operations Runbook.
>
> **Key difference from the GA Developer Guide:** This variant uses `agents-cli scaffold create` for project setup (gets 7 Google skills bundled for free) but `agents-cli eval`, `agents-cli simulate`, and `agents-cli deploy` are **FORBIDDEN**. All evaluation goes through pre-commit hooks + Harness 3-phase pipeline. All deployment goes through Jenkins + Harness CI/CD. Never `agents-cli deploy`.

*Get from "I need an agent" to scaffolded, production-ready code in under 1 hour.*

---

## Quick Start (TL;DR)

If you've done this before and just need the commands:

```bash
# 1. Install preset (one-time)
specify preset add agentcatalyst

# 2. Create project
mkdir my-agent && cd my-agent && specify init --preset agentcatalyst

# 3. In VSCode with your coding agent:
/specify          # fill in the 6-section template → spec.md
/plan             # answer technical questions → plan.md
/catalyst.blueprint   # Connects to Blueprint Advisor MCP Server → agent-blueprint.yaml
# review + edit the YAML
/catalyst.generate    # agents-cli generates everything
```

That's it. Your complete agent project is scaffolded. Skip to [Section 2](#2-greenfield--building-a-new-agent-from-scratch) for the full walkthrough.

---

## Who does what — EA Team vs Developer

Before you write your first `/specify`, understand who provides what:

### What the Enterprise Architecture (EA) team provides

The EA team has already set up everything you need. You don't have to configure any of this:

| What they provide | Where it lives | Why you care |
|---|---|---|
| AgentCatalyst Spec Kit preset | Internal preset catalog | You install it once — it gives you the templates, commands, and reference docs |
| 11 pattern catalog | Vertex AI Search | The Blueprint Advisor searches this to recommend agent patterns |
| Skill catalog | Vertex AI Search | The Blueprint Advisor searches this to recommend skills |
| Tool registry | Apigee API Hub | Approved MCP servers and A2A agents — what you can connect to |
| Blueprint Advisor MCP Server | Cloud Run (GCP) | LlmAgent exposed as MCP Server. Your coding agent calls `recommend_architecture`, `validate_composition`, `assemble_blueprint` via MCP protocol. |
| `agents-cli` | Internal PyPI | The CLI tool that scaffolds your project from the YAML |
| Company overlay skills | Company skills repo | 4 skills (Terraform, observability, CI/CD, security) that teach the coding agent company-specific patterns |
| Company Terraform modules | GitHub (company/tf-modules) | Pre-approved infrastructure modules — you reference them, never write raw TF |

### What you (the developer) do

| Step | What you do | Time |
|---|---|---|
| 1 | Install the preset (one-time) | 2 min |
| 2 | `/specify` — describe your business problem in structured English | 15 min |
| 3 | `/plan` — answer technical questions | 5 min |
| 4 | `/catalyst.blueprint` — get AI architecture advice | 30 sec (wait) |
| 5 | Review and edit the YAML | 10 min |
| 6 | `/catalyst.generate` — generate the entire project | 10 sec |
| 7 | Write FunctionTool bodies + system prompts (the 20%) | 2–4 hours |
| 8 | Commit, PR, CI/CD | Standard process |

**You focus on the business problem. The platform handles the boilerplate.**

---

## 1. Prerequisites

> **Important:** The AgentCatalyst preset includes a `constitution.md` file that encodes non-negotiable rules your coding agent MUST follow (e.g., never deploy directly, never run `agents-cli eval/simulate/deploy`, always use company Terraform modules). These are coding agent constraints — NOT meta-skills or decision frameworks (those exist only in AgentForge). Your coding agent reads constitution.md before generating any code.

> **Important:** The AgentCatalyst preset includes a `constitution.md` file that encodes non-negotiable rules your coding agent MUST follow (e.g., never deploy directly, never run `agents-cli eval/simulate/deploy`, always use company Terraform modules). These are coding agent constraints — NOT meta-skills or decision frameworks (those exist only in AgentForge). Your coding agent reads constitution.md before generating any code.

### 1.1 Workstation requirements

| Tool | Version | Install |
|---|---|---|
| VSCode | Latest | https://code.visualstudio.com |
| A coding agent | Any of: GitHub Copilot, Claude Code, Cursor, Gemini CLI, Windsurf | Install via VSCode extensions or CLI |
| Python | 3.10+ | `brew install python` or company dev container |
| Node.js | 18+ | Required by some coding agents |
| `gh` CLI | Latest | `brew install gh` — needed for `gh skill install` |
| `gcloud` CLI | Latest | `brew install google-cloud-sdk` |
| `agents-cli` | Latest | `uvx google-agents-cli setup` (installs CLI + Google's 7 skills) |
| Git | Latest | Standard |

### 1.2 One-time setup

```bash
# 1. Authenticate with GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Authenticate with GitHub (for skill installation)
gh auth login

# 3. Install agents-cli + Google's 7 skills
uvx google-agents-cli setup

# 4. Install company overlay skills (4 skills)
gemini skills install github.com/company/agentcatalyst-skills --scope user

# 5. Install the AgentCatalyst Spec Kit preset
specify preset add agentcatalyst

# 6. Verify everything is installed
agents-cli --version
```

### 1.3 Verify your skills are visible

Open your coding agent and check that all 11 skills are discovered (7 Google + 4 company):

```
> /skills list

  google-agents-cli-workflow       [built-in]  Always active
  google-agents-cli-adk-code       [built-in]  ADK Python API reference
  google-agents-cli-scaffold       [built-in]  Scaffold commands
  google-agents-cli-eval           [built-in]  Evaluation methodology
  google-agents-cli-deploy         [built-in]  Deployment workflows
  google-agents-cli-publish        [built-in]  Gemini Enterprise registration
  google-agents-cli-observability  [built-in]  Cloud Trace, logging
  company-cicd                     [user]      Company CI/CD (Jenkins + Harness)
  company-terraform-patterns       [user]      Company Terraform modules
  company-observability            [user]      Dynatrace + Splunk + OTel
  company-security                 [user]      Model Armor + VPC-SC + CMEK
```

**If company skills don't appear:** Run `gemini skills install github.com/company/agentcatalyst-skills --scope user` and then `/skills reload`.

**Where skills live on disk:** After installation, company skills are in `~/.agents/skills/` (user scope, available in every project). Alternatively, skills can be checked into your project repo at `.agents/skills/` (workspace scope, shared with the team via git).

| Scope | Directory | Who installs | Available where |
|---|---|---|---|
| User (global) | `~/.agents/skills/` | Developer installs once | Every project on this machine |
| Workspace (project) | `.agents/skills/` in repo root | Checked into git by team | Everyone who clones this repo |
| Built-in | Bundled with agents-cli | `uvx google-agents-cli setup` | Google's 7 skills — everywhere |

### 1.4 VSCode setup

Open VSCode and ensure your coding agent is active:
- **GitHub Copilot:** Check the Copilot icon in the status bar is active
- **Claude Code:** Ensure the Claude extension is installed and authenticated
- **Cursor:** Open Cursor (it's a VSCode fork with AI built in)
- **Gemini CLI:** Open the terminal and run `gemini` to start a session

Open the Copilot Chat panel (or equivalent) — this is where you'll type the `/specify`, `/plan`, and `/catalyst.*` commands.

### 1.5 How skills work (30-second primer)

Skills are instruction manuals that your coding agent reads before writing code. Without skills, your coding agent guesses how to write ADK code. With skills, it follows specific, up-to-date instructions.

**Google's 7 skills** teach your coding agent ADK best practices — the right imports, the right class constructors, the right way to evaluate and observe agents.

**Company's 4 overlay skills** teach your coding agent your company's specific patterns — which Terraform modules to use, how to configure Dynatrace, which Jenkins templates to reference, and how to set up Model Armor.

Your coding agent activates skills on-demand. When you say "generate Terraform," it activates `company-terraform-patterns`. When you say "generate ADK agent classes," it activates `google-agents-cli-adk-code`. It only loads the full instructions when it needs them — keeping the context window lean.

**One important rule:** The company's `company-cicd` skill overrides Google's `google-agents-cli-deploy` skill. This means when you ask the coding agent to "handle deployment," it generates Jenkinsfile + Harness pipeline definitions instead of running `agents-cli deploy` directly. See Section 11 (Deployment Rules) for details.

---

## 2. Greenfield — Building a New Agent from Scratch

This walkthrough uses the FNOL (First Notice of Loss) auto insurance agent as the running example. Replace the insurance details with your own use case.

### 2.1 Initialize the project

```bash
mkdir fnol-agent && cd fnol-agent
specify init --preset agentcatalyst
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

### 2.3 Phase 1: `/specify` — Describe your problem

Type `/specify` in the chat. Your coding agent loads the 6-section template from the preset and presents it. Fill in each section using plain English.

**Tips for writing a great spec:**

| Section | What to write | Pro tip |
|---|---|---|
| **Business Problem** | Who uses this agent, what it automates, why it matters | Be specific about the current pain point and the target improvement |
| **Workflow** | Step-by-step process using ordering words | Use "First," "Then," "Simultaneously," "If [condition]," "Refine until" — these help the Blueprint Advisor pick the right patterns |
| **Data Sources** | System name + access pattern + workload type | Always specify analytical vs transactional vs retrieval — this drives tool selection |
| **External Integrations** | Partner services you don't operate | Say "they operate their own" — this tells the Blueprint Advisor to recommend an A2A connection |
| **Internal Capabilities** | Your proprietary logic | These become FunctionTool implementations — first-draft business logic generated from your spec rules, which you review and refine |
| **Infrastructure** | Region, model, CI/CD, security | Check `memory/infra-standards.md` if unsure about Terraform module versions |

**Example — FNOL Workflow section:**

```
1. First, verify the policyholder's identity and active coverage by
   querying our BigQuery policy data warehouse.
2. Then, extract structured incident details from the caller's description.
3. After extraction, simultaneously enrich with four external sources:
   weather conditions, police report, fraud risk score, coverage details.
4. Generate a claim summary, validate against our quality rubric, and
   refine until the quality score exceeds 0.85.
5. If severity is high or fraud score > 0.7, route to a human adjuster
   for review and approval.
```

When done, the coding agent saves your answers as `spec.md`.

### 2.4 Phase 2: `/plan` — Technical decisions

Type `/plan`. The coding agent asks technical questions from the plan template. Answer each one:

```
Runtime:         agent_engine
GCP Project:     insurance-agents-prod
Region:          us-central1
Model:           gemini-2.0-flash
Garden Template: adk_a2a
TF Modules:      github.com/company/tf-modules
CI/CD:           Jenkins (agent-infra-plan-apply-v3) + Harness (agent-deploy-canary-v4)
Security:        Model Armor: yes, DLP: yes, CMEK: yes, VPC-SC: yes
Observability:   Dynatrace: yes, OTel: yes, Cloud Trace: yes
```

Saved as `plan.md`. You've spent about 20 minutes total.

### 2.5 Phase 3: `/catalyst.blueprint` — Get AI advice

Type `/catalyst.blueprint`. The coding agent connects to the Blueprint Advisor MCP Server and calls the `submit_spec_and_plan` tool with your `spec.md` + `plan.md`.

**What happens behind the scenes (you just wait ~30 seconds):**
1. Blueprint Advisor reads your spec and plan
2. Searches the pattern catalog — finds Coordinator, Sequential, Parallel, Loop, HITL
3. Searches the skill catalog — finds BigQuery skill, fraud-detection skill
4. Searches the tool registry — finds approved MCP servers and A2A endpoints
5. Assembles `agent-blueprint.yaml` with the recommended architecture

The YAML file appears in your workspace. The coding agent shows a summary:

```
Blueprint Advisor recommends:
  5 agents: LlmAgent (coordinator), SequentialAgent (intake),
            ParallelAgent (enrichment), LoopAgent (summary), LlmAgent (HITL)
  3 MCP servers: bigquery-policy, cloud-sql-claims, vertex-search-policies
  3 A2A agents: body-shop-network, rental-car-service, police-report-service
  3 FunctionTool implementations (first draft from spec business rules): severity_classifier, coverage_calculator, notification_sender
  2 skills: bigquery v1.2.0, fraud-detection v2.0.1

Review the YAML and edit any field before running /catalyst.generate.
```

### 2.6 Review and edit the YAML

Open `agent-blueprint.yaml` in the editor. This is your chance to override the Blueprint Advisor's recommendations.

**Common edits:**

| What to check | What to change if wrong |
|---|---|
| Agent topology | Wrong type? Change `type: SequentialAgent` to `type: ParallelAgent` |
| Tool assignment | Tool wired to wrong agent? Change `assigned_to: extract_details` to `assigned_to: fnol_coordinator` |
| Missing tool | Add an entry to `tools.mcp_servers:` or `tools.a2a_agents:` (check `memory/approved-tools.md` for available endpoints) |
| Wrong skill | Change the `name:` or `version:` in `skills:` |
| Model selection | Change `platform.model:` to a different Gemini model |
| Infrastructure | Update Terraform module versions, CI/CD template names |

**Don't worry about getting it perfect** — you can always edit the YAML and re-run `/catalyst.generate` to regenerate the project. The scaffold is deterministic: same YAML → identical output.

### 2.7 Phase 4: `/tasks` — See the breakdown

Type `/tasks`. The coding agent reads the YAML and generates a task breakdown showing what `agents-cli` will generate (80%) vs what you need to implement (20%):

**Auto-generated (you do nothing):**
- 5+ agent class files with correct ADK imports and wiring
- MCP connections with endpoints and auth
- A2A clients with endpoints and timeouts
- Model Armor screening callbacks
- Complete Terraform modules
- Dynatrace + OTel observability config
- Jenkins + Harness pipeline definitions

**You implement (business logic):**
- System prompts for each agent (the "personality" and instructions)
- `severity_classifier()` — classification logic
- `coverage_calculator()` — coverage computation
- `notification_sender()` — notification dispatch
- Test data and evaluation datasets

### 2.8 Phase 5: `/catalyst.generate` — Generate everything

Type `/catalyst.generate`. The coding agent runs:

```bash
agents-cli scaffold create fnol-agent --template adk_a2a
```

In about 10 seconds, your complete project is scaffolded:

```
fnol-agent/
├── app/
│   ├── agent.py                          ← Root LlmAgent (fnol_coordinator)
│   ├── sub_agents/
│   │   ├── intake_pipeline.py            ← SequentialAgent
│   │   ├── enrichment_fan_out.py         ← ParallelAgent
│   │   ├── claim_summary_loop.py         ← LoopAgent
│   │   └── adjuster_review.py            ← LlmAgent (async HITL)
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
│       ├── bigquery/                     ← Installed via gh skill install
│       └── fraud-detection/
├── deployment/terraform/
│   ├── main.tf                           ← Company TF modules referenced
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars
├── observability/
│   ├── dynatrace/
│   │   ├── oneagent-config.yaml
│   │   ├── custom-metrics.json
│   │   └── dashboard-fnol-coordinator.json
│   └── otel/
│       └── otel-collector-config.yaml
├── ci-cd/
│   ├── Jenkinsfile
│   └── harness-pipeline.yaml
├── pyproject.toml
├── README.md
└── agent-blueprint.yaml                  ← The blueprint that generated this
```

Every file follows company patterns. Every generated file has the header comment `# GENERATED by agents-cli — DO NOT EDIT MANUALLY`.

**Notice what `/catalyst.generate` did NOT do:**
- It did NOT run `agents-cli deploy` — there is no direct deployment from your machine
- It did NOT run `agents-cli publish` — agent registration happens after CI/CD deploys to production
- It did NOT generate Cloud Build config — your company uses Jenkins, not Cloud Build
- It did NOT provision any GCP resources — that's Jenkins' job after you merge

Instead, it generated `ci-cd/Jenkinsfile` and `ci-cd/harness-pipeline.yaml` — pipeline definitions that tell your company's CI/CD exactly how to provision infrastructure and deploy the agent. When you commit and merge your PR, Jenkins runs Terraform and Harness deploys through Non-Prod → Pre-Prod → Prod with canary gates.

### 2.9 Write the 20% — What you implement

Now comes the part that requires your domain expertise. Open the files marked "YOUR CODE HERE":

#### System prompts

Open each agent class file and replace `<<< ENGINEER MUST WRITE >>>` with your agent's personality and instructions. Example for the root coordinator:

```python
# app/agent.py — edit the system_instruction
fnol_coordinator = LlmAgent(
    name="fnol_coordinator",
    model="gemini-2.0-flash",
    system_instruction="""You are the FNOL Coordinator for auto insurance claims.
    
    When a policyholder reports an accident, you orchestrate the following:
    1. Verify their identity and coverage (intake_pipeline)
    2. Enrich with external data (enrichment_fan_out)
    3. Generate and refine a claim summary (claim_summary_loop)
    4. Route high-severity or high-fraud claims to an adjuster (adjuster_review)
    
    Be professional, empathetic, and thorough. Always confirm key details
    with the policyholder before proceeding to the next step.""",
    sub_agents=[intake_pipeline, enrichment_fan_out, 
                claim_summary_loop, adjuster_review],
    tools=[notification_sender_tool],
)
```

#### FunctionTool bodies

Open each stub and implement the business logic:

```python
# app/tools/severity_classifier.py
def severity_classifier(claim_data: dict) -> dict:
    """Classify claim severity (low/medium/high)."""
    damage_amount = claim_data.get("estimated_damage", 0)
    injuries = claim_data.get("injuries_reported", False)
    vehicles = claim_data.get("vehicles_involved", 1)
    
    if injuries or damage_amount > 25000 or vehicles > 2:
        return {"severity": "high", "confidence": 0.92}
    elif damage_amount > 5000:
        return {"severity": "medium", "confidence": 0.85}
    else:
        return {"severity": "low", "confidence": 0.95}
```

### 2.10 Commit and let CI/CD take over

```bash
git add .
git commit -m "feat: FNOL agent scaffolded by agents-cli v1.0.0"
git push origin feature/fnol-agent
# Open PR in GitHub
```

Your company's Jenkins/Harness pipelines take it from here: build → test → Non-Prod → Pre-Prod → Prod.

---

## 3. Brownfield — Adding an Agent to an Existing System

Not every agent starts from scratch. Sometimes you're adding an AI agent to an existing system with live data, production APIs, and code you can't modify.

### 3.1 The scenario

You have an existing loan origination system with a REST API, a PostgreSQL database, and a document management service. You want to add an AI agent that assists loan officers by pre-screening applications, but the agent must NOT modify any existing code, database schema, or API contracts.

### 3.2 Initialize Spec Kit in the existing repo

```bash
cd existing-loan-system
specify init --preset agentcatalyst
```

### 3.3 `/specify` with brownfield language

The key difference in brownfield specs is the **External Integrations** and **Internal Capabilities** sections. Instead of describing new services, you describe existing ones:

```markdown
## External Integrations
- Loan origination REST API — WE operate this, it has existing endpoints at
  /api/v2/applications, /api/v2/decisions. The agent MUST use these existing
  endpoints and MUST NOT create new ones.
- Document management service — WE operate this, existing REST API at
  /api/v1/documents. Read-only access for the agent.

## Internal Capabilities
- Credit score lookup — EXISTING internal function, callable via REST at
  /api/v2/credit-check. The agent wraps this as a FunctionTool.
- Compliance rules engine — EXISTING service at /api/v2/compliance-check.
  The agent wraps this, does not reimplement it.
```

### 3.4 The Blueprint Advisor handles brownfield

The Blueprint Advisor reads phrases like "EXISTING REST API," "WE operate this," and "MUST NOT create new ones" and recommends:
- `FunctionTool` wrappers around existing REST endpoints (not new MCP connections)
- Read-only data access patterns
- No Terraform for the existing infrastructure — only for the new agent runtime

### 3.5 Edit the YAML for brownfield

In the generated `agent-blueprint.yaml`, you'll see FunctionTool entries pointing to existing endpoints:

```yaml
tools:
  function_tools:
    - name: loan_application_lookup
      assigned_to: pre_screening_agent
      purpose: "Query existing loan application via /api/v2/applications"
      implementation: engineer_implements  # wrap the existing REST call

    - name: credit_check
      assigned_to: pre_screening_agent
      purpose: "Call existing credit check at /api/v2/credit-check"
      implementation: engineer_implements  # wrap the existing REST call
```

### 3.6 Implement the wrappers

After scaffolding, implement each FunctionTool as a thin wrapper around the existing API:

```python
# app/tools/loan_application_lookup.py
import httpx

def loan_application_lookup(application_id: str) -> dict:
    """Query existing loan application via company REST API.
    
    IMPORTANT: This wraps an EXISTING endpoint. Do not modify the
    existing API or database schema.
    """
    response = httpx.get(
        f"https://loan-api.internal/api/v2/applications/{application_id}",
        headers={"Authorization": f"Bearer {get_secret('loan-api-token')}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
```

**The rule: the agent adapts to the existing system, never the other way around.**

---

## 4. Writing Effective Specs — Signal Words That Help

> For the full list of 11 agentic patterns and how the Blueprint Advisor selects them, see the Architecture Document (Layer 2 section).

> For the full list of 11 agentic patterns and how the Blueprint Advisor selects them, see the Architecture Document (Layer 2 section).

The Blueprint Advisor uses your spec text to search the pattern catalog. Certain words and phrases help it find better matches:

### Words that trigger pattern selection

| What you write | What the Blueprint Advisor infers |
|---|---|
| "First... Then... After that... Finally" | Sequential pipeline (SequentialAgent) |
| "Simultaneously" / "In parallel" / "At the same time" | Parallel fan-out (ParallelAgent) |
| "Generate... validate... refine until" | Loop with quality gate (LoopAgent) |
| "If [condition], route to [human role]" | Human-in-the-loop (LlmAgent + LongRunningFunctionTool) |
| "Coordinate across multiple domains" | Coordinator/Dispatcher (LlmAgent root) |
| "Search documents and reason about results" | Agentic RAG (LlmAgent + Vertex AI Search) |

### Words that trigger tool selection

| What you write | What the Blueprint Advisor recommends |
|---|---|
| "BigQuery" / "data warehouse" / "analytical queries" | BigQuery MCP server |
| "Cloud SQL" / "database" / "transactional" / "create records" | Cloud SQL MCP server |
| "search documents" / "RAG" / "policy corpus" | Vertex AI Search MCP server |
| "they operate their own" / "partner API" | A2A agent connection |
| "our proprietary" / "internal model" | FunctionTool implementation (first draft generated from spec rules; you review and refine) |
| "EXISTING REST API" | FunctionTool wrapper (brownfield pattern) |

### Common mistakes to avoid

| Mistake | Why it's a problem | Better approach |
|---|---|---|
| Vague workflow: "process the claim" | Blueprint Advisor can't determine ordering or parallelism | Break into explicit steps with ordering words |
| Missing workload type: "uses BigQuery" | Blueprint Advisor doesn't know if it's analytical or transactional | Say "BigQuery (analytical queries)" or "BigQuery (read-only)" |
| No ownership signal: "body shop API" | Blueprint Advisor doesn't know if you own it or a partner does | Say "body shop network — they operate their own API" |
| Mixing specs: "process claims AND manage policies" | Too many concerns in one agent | One spec per agent. If you need multiple agents, create multiple specs. |

---

## 4a. Capturing Business Logic in the Spec

If you want the coding agent to generate business logic — not just scaffolding — add four sections to your spec: Business Rules (structured conditions for each decision point), Transformation Rules (field mappings and formulas), Error Handling (timeout/failure/retry behavior per dependency), and Acceptance Criteria (GIVEN/WHEN/THEN assertions per workflow step).

When present, the coding agent generates 90-95% of the code. When omitted, you write business logic manually (~55 additional hours per use case).

**Business Rules** — write inputs, rules as IF/THEN, edge cases, and validation. Example: "IF damage > 25000 OR injuries THEN level=high, routing=adjuster_review." The Blueprint Advisor converts this into `business_rules:` in the YAML. The coding agent generates a working implementation, not a stub.

**Transformation Rules** — write field mappings. Example: "summary.total_damage = body_shop_estimate + rental_cost." The coding agent generates data transformation functions with correct field references.

**Error Handling** — write fallback behavior per dependency. Example: "Body Shop A2A timeout > 30s: use cached estimate, flag for manual review. Retry 2× with exponential backoff." The coding agent generates try/catch blocks with circuit breakers.

**Acceptance Criteria** — write GIVEN/WHEN/THEN per workflow step. The Blueprint Advisor converts these into starter golden dataset entries and pre-populated evalsets in `tests/evalsets/`. Your acceptance criteria become your automated evaluation.

---

## 4b. EvalOps — Your Evaluation Workflow

> For the full EvalOps architecture (3-layer lifecycle, golden dataset lifecycle, meta-evaluation), see the Architecture Document (Layer 4 section). Remember: `agents-cli eval` is FORBIDDEN in this variant — use the pre-commit hook for local evaluation.

> **Golden dataset quality gate:** Your pre-commit hook enforces minimum quality: ≥10 entries per agent, ≥3 edge cases, ≥1 negative test, 100% agent coverage. If your golden dataset doesn't meet these thresholds, the commit is blocked. The entries generated from your acceptance criteria are a starting point — you need to add edge cases and negative tests during development.

> For the full EvalOps architecture (3-layer lifecycle, golden dataset lifecycle, meta-evaluation), see the Architecture Document (Layer 4 section). Remember: `agents-cli eval` is FORBIDDEN in this variant — use the pre-commit hook for local evaluation.

AgentCatalyst generates a complete evaluation lifecycle. The `company-cicd` and `company-observability` skills generate everything automatically.

**What gets generated:** `tests/eval_inner_loop.py` (pre-commit hook — blocks commit if any metric drops >10%), `.pre-commit-config.yaml`, `observability/adk-tracing-config.py` (ADK tracing), `observability/phoenix-config.py` (Arize Phoenix at `localhost:6006`), `golden-dataset/golden-v1.json` (from acceptance criteria), and `harness-pipeline.yaml` (3-phase: Arize eval → AutoSxS comparison → HITL triage).

**Your daily workflow:** Edit code → `git commit` → pre-commit inner loop catches regressions in <60 seconds → push → Harness runs 3-phase eval → production with Arize monitoring → drift detected → failing cases sampled → human annotates → golden dataset updated.

**Debugging with Phoenix:** When evaluation fails, open `localhost:6006` to see the full agent trace — which agent failed, which tool returned bad data, whether a loop converged. This replaces the pass/fail black box with "X-ray vision" into agent reasoning.

Note: `agents-cli eval` is forbidden by three-layer skill override. The pre-commit inner loop + Harness pipeline replaces it entirely.

---

## 5. Understanding the YAML Blueprint

> **If the Blueprint Advisor is unavailable:** You can author `app-blueprint.yaml` manually using the YAML schema below and the FNOL example in the Architecture Document (Appendix A.10) as a template. The `/catalyst.generate` command only needs the YAML file — it does not require the MCP Server. You lose the AI-guided recommendation but are not blocked from generating code.

> **How the YAML is created:** Your coding agent calls `recommend_architecture(spec, plan)` on the Blueprint Advisor MCP Server. The server runs the Blueprint Advisor LlmAgent internally (RAG search + LLM reasoning + company system prompt) and returns recommendations with confidence scores. Your coding agent then calls `validate_composition(pattern_tree)` to check your edits, and `assemble_blueprint(selections, spec, plan)` to finalize the YAML. All three calls happen via MCP protocol (v2025-03-26) — your coding agent never accesses Vertex AI Search or the LlmAgent directly. See the Architecture Document (Layer 2) for the full MCP Server tool table, security controls, and rate limiting.

> **How the YAML is created:** Your coding agent calls `recommend_architecture(spec, plan)` on the Blueprint Advisor MCP Server. The server runs the Blueprint Advisor LlmAgent internally (RAG search + LLM reasoning + company system prompt) and returns recommendations with confidence scores. Your coding agent then calls `validate_composition(pattern_tree)` to check your edits, and `assemble_blueprint(selections, spec, plan)` to finalize the YAML. All three calls happen via MCP protocol — your coding agent never accesses Vertex AI Search or the LlmAgent directly. See the Architecture Document (Layer 2) for the full MCP Server tool table.

The `agent-blueprint.yaml` is the single source of truth for what `agents-cli` will scaffold. Here's a field-by-field guide:

### metadata

```yaml
metadata:
  name: fnol-coordinator       # Used for: project folder name, agent name
  version: "1.0.0"             # Used for: README, tracking
  garden_template: adk_a2a     # Used for: which Garden template to clone
  description: "FNOL agent"    # Used for: README header
```

### agents

```yaml
agents:
  - name: fnol_coordinator     # Becomes: app/agent.py
    type: LlmAgent             # ADK class to use
    role: "Root coordinator"   # Becomes: class docstring
    sub_agents:                # Wired in constructor
      - intake_pipeline
      - enrichment_fan_out
```

**Type determines the file content:**
- `LlmAgent` → generates model assignment, system_instruction placeholder, tools list
- `SequentialAgent` → generates sub_agents in order (steps field)
- `ParallelAgent` → generates sub_agents as parallel branches
- `LoopAgent` → generates max_iterations and exit_condition

### tools

```yaml
tools:
  mcp_servers:
    - name: bigquery-policy    # Becomes: app/mcp_connections/bigquery_policy.py
      endpoint: bigquery...    # Wired into MCPToolset connection_params
      transport: sse           # Protocol
      auth: workload_identity  # Auth method
      assigned_to: verify_policy  # Wired to this agent's tools list
```

**The `assigned_to` field is critical** — it determines which agent gets access to which tool. If a tool is assigned to the wrong agent, that agent won't have access to it at runtime. Review this carefully.

### skills

```yaml
skills:
  - name: bigquery             # Installed via: gh skill install {source} bigquery@1.2.0
    source: github.com/company/agent-skills
    version: "1.2.0"           # Pinned — provenance SHA verified on install
    assigned_to: verify_policy # Wired to this agent's SkillToolset
```

### infrastructure

```yaml
infrastructure:
  terraform:
    modules:
      - name: agent-runtime    # Becomes: module "agent-runtime" in main.tf
        source: github.com/company/tf-modules//agent-runtime
        version: v3.1.0        # MUST be pinned — no "latest"
```

**All modules must be from the company's approved Terraform module registry.** Check `memory/infra-standards.md` for available modules and current versions.

### diagrams

The Blueprint Advisor generates three Mermaid diagrams at the bottom of the YAML in a `diagrams:` section. These are not separate files — they're part of the same `agent-blueprint.yaml` you already review.

| Diagram | What you see | What to check |
|---|---|---|
| **Component** | Agent tree with boxes for each agent, connected to their tools (MCP servers as cylinders, A2A as hexagons, FunctionTools as parallelograms) | "Does each agent connect to the right tools? Are any tools orphaned or assigned to the wrong agent?" |
| **Sequence** | Step-by-step message flow showing what happens at runtime — Sequential phases in order, Parallel branches side-by-side, Loop iterations, HITL routing | "Does the flow match my spec's Workflow section? Are the parallel branches correct? Does HITL route on the right condition?" |
| **Infrastructure** | GCP services inside VPC-SC boundary, external partners outside, CI/CD pipeline connections | "Are all the services I need inside the perimeter? Are external partners shown correctly?" |

**How to view them:** Open `agent-blueprint.yaml` in VSCode. If you have a Mermaid preview extension installed (most setups do), the diagrams render automatically in the preview pane. You can review the YAML fields on the left and see the architecture visually on the right.

**How to edit them:** The diagrams are Mermaid text — you can edit agent names, add notes, adjust layout. If you change the `agents:` or `tools:` sections and re-run `/catalyst.blueprint`, the diagrams regenerate to match.

**How to export them:** If you need PNG/SVG for documentation or a presentation, your CI pipeline can render them automatically. Or locally: `npx -p @mermaid-js/mermaid-cli mmdc -i diagram.mmd -o diagram.png`.

**Pro tip:** During PR review, GitHub and GitLab render Mermaid blocks natively. Your team sees the architecture diagram right in the PR — no extra steps needed.

---

## 6. Re-scaffolding — Iterating on the Design

One of the biggest advantages of skill-guided generation: you can change the YAML and re-run `/catalyst.generate` as many times as you want.

### When to re-scaffold

| Scenario | What to do |
|---|---|
| Blueprint Advisor got the topology wrong | Edit `agents:` section, re-run `/catalyst.generate` |
| Need to add a new tool | Add to `tools.mcp_servers:` or `tools.a2a_agents:`, re-scaffold |
| ADK version update | Google updates agents-cli skills for new ADK; re-generate with same YAML |
| Switching CI/CD templates | Edit `infrastructure.cicd:`, re-generate |

### What happens to your custom code?

**Warning:** `agents-cli scaffold` generates a fresh project from the YAML. If you re-scaffold into the same output directory, it overwrites generated files. Your options:

1. **Re-scaffold to a new directory**, then diff against your existing project:
   ```bash
   agents-cli scaffold create fnol-agent --template adk_a2a-v2
   diff -r fnol-agent fnol-agent-v2
   ```

2. **Keep custom code separate.** The generated files are marked `# GENERATED — DO NOT EDIT MANUALLY`. Your refinements live in the FunctionTool implementations (reviewing and refining the generated first-draft logic) and system prompts. If you follow this convention, you can identify generated vs custom code easily.

3. **Use git.** Commit before re-scaffolding. After re-scaffold, `git diff` shows exactly what changed.

---

## 7. Troubleshooting

> For platform-level failure modes and escalation procedures, see the Operations Runbook, Section 6 (Failure Modes) and Section 9 (MCP Server Operations). If the Blueprint Advisor MCP Server is unreachable or returning errors, contact Platform Engineering per the escalation matrix in the Operations Runbook.

### Common issues

| Problem | Cause | Fix |
|---|---|---|
| `/catalyst.blueprint` returns error | Blueprint Advisor API unreachable | Check `CATALYST_BLUEPRINT_API` env var. Try `curl $CATALYST_BLUEPRINT_API/health`. |
| `/catalyst.generate` says "YAML validation failed" | Invalid YAML schema | Run `agents-cli scaffold validate --config agent-blueprint.yaml` for specific errors. Common: missing `assigned_to`, unpinned module version, invalid agent type. |
| Skill provenance check fails | Skill has been updated since YAML was generated | Update the `version:` in the YAML to match the current version. Or run `gh skill list {source}` to see available versions. |
| `agents-cli` not found | CLI not installed | Run `uvx google-agents-cli setup`. |
| Generated code doesn't compile | Skill version mismatch or ADK version change | Check `agents-cli --version` is latest. Report to platform engineering. |
| Blueprint Advisor recommends wrong pattern | Spec is ambiguous | Rewrite the Workflow section with clearer ordering words (see Section 4). |
| YAML is missing a tool I need | Blueprint Advisor didn't find it | Check `memory/approved-tools.md` for available tools. Add the tool manually to the YAML. If the tool isn't approved yet, request it from platform engineering. |
| Coding agent tries to run `agents-cli deploy` | Default workflow skill overriding company rules | Verify company overlay skills are installed (`gemini skills install github.com/company/agentcatalyst-skills --scope user`). Check `GEMINI.md` has the workflow override table. Re-run `/catalyst.generate` which includes explicit skip instructions. |
| Coding agent generates Cloud Build config | Default deploy skill used instead of company-cicd | Same fix as above — ensure company skills override. Delete any generated `cloudbuild.yaml` and re-run `/catalyst.generate`. |
| Company overlay skills not visible to coding agent | Skills not installed or wrong directory | Run `gemini skills install github.com/company/agentcatalyst-skills --scope user`. Check with `/skills` command in your coding agent to verify all 11 skills are visible (7 Google + 4 company). |

### Getting help

| Channel | When to use |
|---|---|
| `#agentcatalyst` Slack channel | General questions, peer help |
| Platform Engineering JIRA | Bugs in `agents-cli`, template issues, new tool requests |
| EA team office hours | Pattern questions, spec reviews, architecture guidance |

---

## 8. Reference — All Commands

| Command | What it does | Prerequisites |
|---|---|---|
| `specify init --preset agentcatalyst` | Initialize project with AgentCatalyst preset | Preset installed via `specify preset add agentcatalyst` |
| `/specify` | Present the 6-section spec template | Project initialized |
| `/plan` | Present the technical plan template | `spec.md` exists |
| `/catalyst.blueprint` | Submit spec + plan to Blueprint Advisor, receive YAML | `spec.md` + `plan.md` exist, API configured |
| `/catalyst.generate` | Run `agents-cli scaffold` against YAML | `agent-blueprint.yaml` exists, `agents-cli` installed |
| `/tasks` | Generate task breakdown (generated vs engineer) | `agent-blueprint.yaml` exists |
| `agents-cli scaffold --config X --output Y` | Scaffold directly from terminal | YAML file exists |
| `agents-cli validate --config X` | Validate YAML without scaffolding | YAML file exists |
| `agents-cli scaffold --dry-run --config X --output Y` | Show what would be generated | YAML file exists |

---

## 9. Reference — Preset File Map

Every file in the `.specify/` folder serves a specific purpose:

```
.specify/
├── preset.yml                    ← Manifest: which files, which agents, settings
│
├── templates/
│   ├── spec-template.md          ← /specify loads this — 6 sections with
│   │                                coaching prompts and examples
│   ├── plan-template.md          ← /plan loads this — technical questions
│   │                                mapping to YAML fields
│   └── tasks-template.md        ← /tasks loads this — generated vs
│                                    engineer split table
│
├── commands/
│   ├── catalyst.blueprint.md    ← /catalyst.blueprint — instructions for
│   │                                the coding agent to call Blueprint
│   │                                Advisor API and save YAML
│   └── catalyst.generate.md     ← /catalyst.generate — instructions for
│                                    the coding agent to run agents-cli
│
└── memory/
    ├── adk-reference.md          ← ADK class reference — loaded into
    │                                coding agent context during /specify
    │                                and /plan for coaching
    ├── company-patterns.md       ← Company naming conventions, folder
    │                                structure, code standards
    ├── approved-tools.md         ← Approved MCP servers + A2A agents
    │                                with endpoints and auth
    └── infra-standards.md        ← TF module registry, version pinning
                                     rules, CI/CD templates, security defaults
```

---

## 10. FAQ

**Q: Can I write the YAML manually without using the Blueprint Advisor?**
A: Yes. `agents-cli` reads the YAML file — it doesn't care who or what produced it. You can write `agent-blueprint.yaml` by hand, copy from a teammate, or generate it with any tool. The Blueprint Advisor is a convenience, not a requirement.

**Q: Can I use a different coding agent for `/specify` and a different one for `/catalyst.generate`?**
A: Yes. Spec Kit works with 30+ coding agents. You can run `/specify` in Copilot, review in Cursor, and run `/catalyst.generate` in Claude Code. The preset files are the same regardless of agent.

**Q: What if my use case needs a pattern that's not in the catalog?**
A: Request it from the EA team (see Governance section in the architecture doc). They'll evaluate, document the pattern, and add it to the catalog. In the meantime, you can write the YAML manually with the agent topology you need — `agents-cli` scaffolds from the YAML, not from the pattern catalog.

**Q: What if I need a tool that's not on the approved list?**
A: Request it from Platform Engineering (see `memory/approved-tools.md` for the process). They'll validate the endpoint, security posture, and SLA before adding it. In the meantime, you can add the tool to your YAML manually — `agents-cli` will scaffold the connection, but the tool won't be in the tool registry for other teams to discover.

**Q: Can I re-scaffold after I've already written custom code?**
A: Yes, but scaffold to a new directory and diff. See Section 6 for details.

**Q: Is the generated code production-ready or just a starting point?**
A: It's production-ready boilerplate — the coding agent uses Google's `google-agents-cli-adk-code` skill for correct ADK imports and tool wiring, plus company overlay skills for Terraform, observability, and CI/CD. You add: system prompts, FunctionTool business logic, and test data. The scaffold is the 80%; your domain expertise is the 20%.

**Q: Why is the scaffold deterministic instead of using an LLM?**
A: Through skills. Google's 7 agents-cli skills teach the coding agent ADK best practices. Company overlay skills teach enterprise-specific patterns. The skills constrain the LLM's output so generated code follows both Google's standards and company standards. Two runs produce functionally equivalent code — same agent classes, same tool wiring — though variable names and comments may vary slightly.

**Q: Can I use `agents-cli deploy` to quickly test in a dev environment?**
A: No — not in this company's workflow. `agents-cli deploy` pushes directly from your machine, bypassing code review and company CI/CD. Even for dev environments, commit your code and let Jenkins/Harness deploy. If you need to test locally before committing, use `agents-cli playground` or `adk web` to run the agent on your machine.

**Q: Why does my GEMINI.md say "DO NOT use agents-cli deploy"?**
A: The AgentCatalyst preset replaces the default `GEMINI.md` with a company version that includes workflow overrides. This ensures your coding agent follows the company lifecycle (generate CI/CD files) instead of the default agents-cli lifecycle (deploy directly). Do not delete or modify the override section of `GEMINI.md`.

---

## 11. Deployment Rules — What NOT to Do

> **CRITICAL for this variant:** `agents-cli eval`, `agents-cli simulate`, and `agents-cli deploy` are **FORBIDDEN**. This is enforced at three layers:
>
> | Layer | Enforcement |
> |---|---|
> | company-cicd skill | Tells coding agent: "Generate pipeline files. NEVER deploy directly." |
> | constitution.md | Absolute rule: "NEVER run `agents-cli eval`, `agents-cli simulate`, or `agents-cli deploy`." |
> | `.agentcli-overrides.yaml` | Disables eval/simulate/deploy at the CLI level — even if the coding agent tries |
>
> See the Architecture Document (Layer 3 — FORBIDDEN commands section) for the full rationale and defense-in-depth design.

> **CRITICAL for this variant:** `agents-cli eval`, `agents-cli simulate`, and `agents-cli deploy` are **FORBIDDEN**. This is enforced at three layers:
>
> | Layer | Enforcement |
> |---|---|
> | company-cicd skill | Tells coding agent: "Generate pipeline files. NEVER deploy directly." |
> | constitution.md | Absolute rule: "NEVER run `agents-cli eval`, `agents-cli simulate`, or `agents-cli deploy`." |
> | `.agentcli-overrides.yaml` | Disables eval/simulate/deploy at the CLI level — even if the coding agent tries |
>
> All evaluation goes through pre-commit hooks (Layer 1) + Harness 3-phase pipeline (Layer 3). All deployment goes through Jenkins + Harness CI/CD. See the Architecture Document (Layer 3 — FORBIDDEN commands section) for the full rationale.

This section exists because `agents-cli` ships with `deploy`, `eval`, and `simulate` commands that your coding agent might try to use. **In this company, none of these are permitted from your developer machine. All deployment and evaluation happens via CI/CD.**

### The rules

| ❌ Never do this | ✅ Do this instead |
|---|---|
| `agents-cli deploy` | Commit code → PR → Jenkins (Terraform) → Harness (canary deploy) |
| `agents-cli eval` | Write evalsets locally; Harness runs them via Arize against the deployed agent |
| `agents-cli simulate` | Write simulation scenarios locally; Harness runs them via Arize multi-turn evaluation |
| `agents-cli publish` | Agent registration is a post-deployment step in the Harness pipeline |
| Generate Cloud Build config | Company uses Jenkins, not Cloud Build |
| Provision GCP resources from your machine | Jenkins runs Terraform after PR merge |
| Modify `GEMINI.md` workflow override section | Leave the override intact — it prevents your coding agent from running these commands |

### Why these rules exist

**For `agents-cli deploy`** — pushing code directly from your laptop means:
- **No code review** — your PR hasn't been approved
- **No Terraform** — infrastructure isn't provisioned via approved modules
- **No canary deployment** — the agent goes straight to 100% traffic
- **No rollback** — if it breaks, there's no automated rollback
- **No audit trail** — the deployment isn't tracked

**For `agents-cli eval` and `agents-cli simulate`** — these commands call **Agent Evaluation Service** and **Agent Simulation Service** respectively, which are **pre-GA preview services**. Production GCP projects in this company often don't have preview APIs enabled, for two reasons:
1. **No SLA** — preview services can have downtime or be deprecated without notice
2. **Compliance** — some regulated environments only permit GA services

If your coding agent calls these from a developer workstation, it might work in your project but break for someone else. The CI/CD pipeline uses **Arize** instead, which is a GA SaaS that runs reliably in any environment.

### How evaluation actually works

Your job as a developer:

1. **Write evalsets locally** in `tests/evalsets/`:
   ```json
   // tests/evalsets/fnol-basic.json
   [
     {
       "test_id": "fnol-001",
       "input": "I was in a car accident on I-85. Policy P-12345.",
       "expected_tool_calls": ["bigquery-policy.execute_query"],
       "expected_agent_sequence": ["fnol_coordinator", "intake_pipeline", "verify_policy"],
       "expected_output_contains": ["policy verified", "active coverage"],
       "max_latency_ms": 3000
     }
   ]
   ```

2. **Run unit tests locally** with `pytest` (uses mocks, no GCP services required):
   ```bash
   pytest tests/unit/   # Fast feedback, runs on every save
   ```

3. **Commit evalsets with your code**. Don't run `agents-cli eval` — Harness will run Arize against the deployed agent.

4. **After PR merge**, Harness pipeline:
   - Deploys agent to non-prod
   - Runs Arize evaluation against your evalsets
   - Quality gates: pass rate ≥ 95%, p95 latency ≤ 3s, hallucination ≤ 0.15
   - If gates pass, promotes to pre-prod, runs again
   - If gates pass, canary deploys to prod

5. **View results** in Arize dashboard (link is in the Harness pipeline output).

### What happens after you commit

```
You commit + open PR
    ↓
Team reviews PR (code review)
    ↓
PR merged to main
    ↓
Jenkins pipeline triggers automatically:
    1. Terraform init
    2. Terraform plan (generates infrastructure plan)
    3. OPA policy check (validates against company policies)
    4. Terraform apply (provisions Cloud Run, Cloud SQL,
       Vertex AI Search, Model Armor, VPC-SC, CMEK)
    ↓
Harness pipeline triggers automatically:
    1. Build container image
    2. Deploy to Non-Prod
    3. Run Arize evaluation against Non-Prod agent
       (uses your evalsets in tests/evalsets/)
    4. Quality gate: pass_rate ≥ 95%, p95_latency ≤ 3s
    5. If passing, deploy to Pre-Prod (canary at 10% traffic)
    6. Run Arize evaluation against Pre-Prod
    7. Validate SLOs (latency, error rate, success rate)
    5. If SLOs pass → deploy to Production (progressive rollout)
    6. If SLOs fail → automatic rollback
```

You don't need to do anything after merging your PR. The pipelines handle everything.

---

## 12. A Concrete Deployment Scenario

> See the Architecture Document (Layer 4) for the full CI/CD architecture — Jenkins infrastructure plane + Harness application plane with 3-phase EvalOps. `agents-cli deploy` is FORBIDDEN — all deployment goes through Jenkins + Harness.

> See the Architecture Document for the full CI/CD architecture (Layer 4 — Jenkins infrastructure plane + Harness application plane with 3-phase EvalOps). `agents-cli deploy` is FORBIDDEN — all deployment goes through Jenkins + Harness. — FNOL Agent Merge to Production

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

The reason AgentCatalyst forbids `agents-cli deploy` and forces this two-plane model is governance. Each plane enforces a specific control:

| Governance concern | How it's enforced |
|---|---|
| Infrastructure follows company standards | Jenkins runs OPA policy checks before Terraform apply |
| All changes are traceable | Every deployment has Jenkins run ID + Harness execution ID logged in Splunk |
| Production deployments require approval | Harness manual approval gate before pre-prod promotion |
| Quality gates protect production | Arize evaluation must pass before each environment promotion |
| Bad deployments don't take down production | Canary deployment + automatic SLO-based rollback in Harness |
| No one can bypass the pipeline | `agents-cli deploy` is forbidden by three-layer skill override; CI/CD is the only path |

If you ran `agents-cli deploy` from your workstation, none of this would happen. The agent would go straight to 100% traffic with no policy checks, no quality gates, no canary, no rollback, no audit trail. That's the failure mode AgentCatalyst prevents.

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

## Appendix A — AgentCatalyst Preset (Complete Code)

This appendix contains the full source of every file in the AgentCatalyst Spec Kit preset. When a developer runs `specify preset add agentcatalyst`, these files are installed into their project's `.specify/` folder.

### Directory structure

```
.specify/
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

---

### preset.yml

```yaml
# AgentCatalyst Preset for GitHub Spec Kit
# Install: specify preset add agentcatalyst
# Source: github.com/[company]/agentcatalyst-preset

name: agentcatalyst
version: "1.0.0"
description: >
  AgentCatalyst enterprise agent development accelerator.
  Structured requirements capture, AI-assisted architecture advice
  via Blueprint Advisor, and skill-guided generation via agents-cli.

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

settings:
  coding_agents:
    - copilot
    - claude-code
    - gemini-cli
    - cursor
    - windsurf
  output_format: markdown
  save_location: workspace_root
```

---

### templates/spec-template.md

```markdown
---
template: agentcatalyst-spec
version: "1.0.0"
description: Structured requirements template for agentic AI applications
usage: Run /specify to fill in this template with your coding agent
---

# Agent Specification

## Business Problem

<!-- 
WHAT TO WRITE HERE:
Describe the business process this agent will automate. Be specific about:
- Who are the end users? (e.g., policyholders, customer service reps, analysts)
- What is the current pain point? (e.g., manual processing takes 3 days)
- What business value does automation provide? (e.g., reduce processing time to minutes)
- What is the scope boundary? (e.g., handles first notice only, not full claim lifecycle)

EXAMPLE:
"We need an AI agent that handles First Notice of Loss (FNOL) for auto insurance.
When a policyholder reports an accident via phone or web, the agent should verify
their policy, collect incident details, assess severity, and either auto-approve
low-severity claims or route high-severity ones to a human adjuster. Currently
this process takes 3-5 days manually. The agent should reduce it to under 1 hour."
-->

[Describe your business problem here]

## Workflow

<!--
WHAT TO WRITE HERE:
Describe the step-by-step workflow the agent should follow. Be specific about:
- ORDERING: Which steps happen first, second, third? Use words like "First,"
  "Then," "After that," "Finally" for sequential steps.
- PARALLELISM: Which steps can happen at the same time? Use words like
  "Simultaneously," "In parallel," "At the same time" for concurrent steps.
- CONDITIONS: Are there decision points? Use "If [condition], then [action]"
- HUMAN REVIEW: Does a human need to approve anything? Use "Route to [role]
  for review" or "Requires human approval"
- ITERATION: Does anything need to repeat? Use "Generate... validate...
  refine until [threshold]"

EXAMPLE:
"1. First, verify the policyholder's identity and active coverage by querying
    our BigQuery policy data warehouse.
 2. Then, extract structured incident details from the caller's description.
 3. After extraction, simultaneously enrich with four external data sources:
    weather conditions, police report, fraud risk score, and coverage details.
 4. Generate a claim summary, validate it against our quality rubric, and
    refine until the quality score exceeds 0.85.
 5. If the severity is high or the fraud score exceeds 0.7, route to a
    human adjuster for review and approval."
-->

[Describe your workflow step by step here]

## Data Sources

<!--
WHAT TO WRITE HERE:
List every data system the agent needs to access. For each, specify:
- System name (e.g., BigQuery, Cloud SQL, Vertex AI Search)
- Access pattern: read-only or read-write?
- Workload type: analytical (complex queries, aggregations) or 
  transactional (single-row CRUD operations) or storage (file upload/download)
  or retrieval (document search, RAG)?

EXAMPLE:
"- BigQuery: policy data warehouse (read-only, analytical queries —
   aggregate coverage data, policy history lookups)
 - Cloud SQL: claims database (read-write, transactional — create new
   claim records, update claim status)
 - Vertex AI Search: policy document corpus (read-only, retrieval —
   search policy documents for coverage questions)"
-->

[List your data sources here]

## External Integrations

<!--
WHAT TO WRITE HERE:
List any partner APIs, third-party services, or external agents the agent
needs to communicate with. For each, specify:
- Who operates the service? (the key question — is it yours or theirs?)
- How is it accessed? (REST API, A2A agent protocol, webhook, etc.)
- What does the agent need from it?

EXAMPLE:
"- Body shop repair network — they operate their own quoting service.
   We send vehicle details, they return repair estimates.
 - Rental car provider — they operate their own availability API.
   We send dates and location, they return options.
 - Police report service — municipal system, we don't control it.
   We send incident ID, they return the report."
-->

[List your external integrations here]

## Internal Capabilities

<!--
WHAT TO WRITE HERE:
List any proprietary models, internal APIs, or company-specific business
logic the agent needs. These will become FunctionTool implementations — first-draft business logic that developers review and
implement with actual business logic.

EXAMPLE:
"- Our proprietary fraud detection model (takes claim data, returns
   fraud probability score 0.0-1.0)
 - Our proprietary severity classification algorithm (takes incident
   details, returns low/medium/high severity)
 - Claim notification service (sends acknowledgment emails and SMS)"
-->

[List your internal capabilities here]

## Infrastructure Requirements

<!--
WHAT TO WRITE HERE:
Specify the deployment and operational requirements:
- GCP region (e.g., us-central1)
- LLM model preference (e.g., gemini-2.0-flash, gemini-2.0-pro)
- CI/CD tools (e.g., Jenkins for infra, Harness for deployment)
- Security requirements (e.g., Model Armor, DLP, CMEK, VPC-SC)
- Compliance constraints (e.g., PII masking, audit logging, data residency)

EXAMPLE:
"- Region: us-central1
 - Model: gemini-2.0-flash (latency-sensitive workflow)
 - CI/CD: Jenkins for infrastructure provisioning, Harness for deployment
 - Security: Model Armor enabled, DLP for PII detection, CMEK for
   encryption at rest, VPC-SC perimeter around production
 - Compliance: All claim decisions must be auditable, PII masked in logs,
   state insurance regulations require acknowledgment within 24 hours"
-->

[Specify your infrastructure requirements here]
```

---

### templates/plan-template.md

```markdown
---
template: agentcatalyst-plan
version: "1.0.0"
description: Technical decisions template mapping to agent-blueprint.yaml fields
usage: Run /plan to answer these technical questions
---

# Technical Plan

## Target Platform

<!-- Which GCP runtime will host the agent? -->
- **Runtime:** [agent_engine | cloud_run]
- **GCP Project:** [project-id]
- **GCP Region:** [e.g., us-central1]

## Model Selection

<!-- Which LLM will the agent use? -->
- **Primary model:** [e.g., gemini-2.0-flash]
- **Reasoning model (if different):** [e.g., gemini-2.0-pro for complex steps]

## Agent Garden Template

<!-- Which starter template to clone? -->
- **Template:** [adk | adk_a2a | agentic_rag]

## Infrastructure

<!-- Where do your Terraform modules live? -->
- **Terraform module source:** [e.g., github.com/company/tf-modules]
- **Module version pinning strategy:** [e.g., exact version tags like v3.1.0]

## CI/CD

<!-- Which pipeline tools does your team use? -->
- **Infrastructure pipeline:** [e.g., Jenkins — template: agent-infra-plan-apply-v3]
- **Deployment pipeline:** [e.g., Harness — template: agent-deploy-canary-v4]

## Security

<!-- Which security controls are required? -->
- **Model Armor:** [yes | no]
- **DLP:** [yes | no]
- **CMEK:** [yes | no — if yes, key ring path]
- **VPC-SC perimeter:** [yes | no]

## Observability

<!-- Which monitoring tools are in use? -->
- **Dynatrace:** [yes | no]
- **OpenTelemetry Collector:** [yes | no]
- **Cloud Trace:** [yes | no]
- **Cloud Logging:** [yes | no]
- **Splunk forwarding:** [yes | no]

## Additional Constraints

<!-- Any other technical requirements or constraints? -->
[List any additional constraints here]
```

---

### templates/tasks-template.md

```markdown
---
template: agentcatalyst-tasks
version: "1.0.0"
description: Task breakdown template separating generated vs engineer-implemented work
usage: Run /tasks after receiving agent-blueprint.yaml to generate the task list
---

# Task Breakdown

## Auto-generated by agents-cli (engineer does nothing)

<!-- agents-cli generates these from agent-blueprint.yaml -->

| Component | Source (YAML section) | Status |
|---|---|---|
| ADK agent class hierarchy | agents: | ⬜ Will be generated |
| MCP server connections | tools.mcp_servers: | ⬜ Will be generated |
| A2A agent client connections | tools.a2a_agents: | ⬜ Will be generated |
| Skills installed + wired | skills: | ⬜ Will be generated |
| Model Armor callbacks | infrastructure.security | ⬜ Will be generated |
| Terraform modules | infrastructure.terraform | ⬜ Will be generated |
| Dynatrace + OTel config | infrastructure.observability | ⬜ Will be generated |
| CI/CD pipeline definitions | infrastructure.cicd | ⬜ Will be generated |

## Engineer implements (business logic — the 20%)

<!-- These require domain expertise the scaffold cannot provide -->

| Component | What to implement | Priority |
|---|---|---|
| System prompts | Write agent personality + instructions for each agent node | P0 — agents won't work without prompts |
| FunctionTool review | Review and refine first-draft business logic generated from spec rules | P0 — core functionality |
| Test data | Create test cases and evaluation datasets | P1 — needed before CI/CD |
| Domain guardrails | Add business-specific validation rules beyond Model Armor | P2 — hardening |
```

---

### commands/catalyst.blueprint.md

```markdown
---
name: catalyst.blueprint
description: Submit spec + plan to the Blueprint Advisor and receive an agent-blueprint.yaml
---

# Generate Architecture Blueprint

Submit the structured specification and technical plan to the Blueprint Advisor
for AI-assisted architecture recommendations.

## Prerequisites

- `spec.md` exists in the workspace root (generated by /specify)
- `plan.md` exists in the workspace root (generated by /plan)
- Blueprint Advisor API endpoint is configured in environment variable
  `CATALYST_BLUEPRINT_API` or in `.specify/config.yaml`

## Steps

1. Read `spec.md` from the workspace root
2. Read `plan.md` from the workspace root
3. Validate both files are non-empty and contain the required sections
4. Submit to the Blueprint Advisor API:
   ```
   MCP call: submit_spec_and_plan(spec, plan, archetype) via mcp://blueprint-advisor.[company-domain].run.app
   Content-Type: application/json
   
   {
     "spec": "<contents of spec.md>",
     "plan": "<contents of plan.md>"
   }
   ```
5. Receive `agent-blueprint.yaml` from the response
6. Save `agent-blueprint.yaml` to the workspace root
7. Display a summary of the recommended architecture:
   - Number of agents and their types
   - Number of MCP servers, A2A agents, and FunctionTool implementations
   - Infrastructure summary (Terraform modules, CI/CD templates)
8. Remind the developer: "Review the YAML and edit any field before
   running /catalyst.generate. The Blueprint Advisor recommends —
   you decide."

## Error Handling

- If `spec.md` or `plan.md` is missing: prompt the developer to run
  /specify and /plan first
- If the Blueprint Advisor API is unreachable: display connection error
  and suggest checking the API endpoint configuration
- If the response is invalid YAML: display the raw response and suggest
  the developer contact the platform engineering team
```

---

### commands/catalyst.generate.md

```markdown
---
name: catalyst.generate
description: Run agents-cli to scaffold the agent project from agent-blueprint.yaml
---

# Scaffold Agent from Blueprint

Run agents-cli to generate a fully scaffolded, production-ready agent project
from the agent-blueprint.yaml in the current workspace.

## Prerequisites

- `agent-blueprint.yaml` exists in the workspace root
  (generated by /catalyst.blueprint or created manually)
- `agents-cli` is installed and available on PATH
  (install via: uvx google-agents-cli setup)
- `agents-cli` is installed (for Garden template cloning)
- `gh` CLI is installed with skill extension (for skill installation)

## Steps

1. Locate `agent-blueprint.yaml` in the workspace root
2. Validate the YAML structure:
   - Required sections: metadata, platform, agents, tools, infrastructure
   - All agent names are valid snake_case
   - All assigned_to references point to existing agent names
   - All module versions are pinned (no "latest")
3. Run scaffold:
   ```bash
   agents-cli scaffold \
     --config agent-blueprint.yaml \
     --output ./${metadata.name}
   ```
4. Report results:
   - Total files generated
   - Files for developer review (FunctionTool implementations with first-draft business logic)
   - Any validation warnings from Step 12 (company coding standards)
5. Open `app/agent.py` for the developer to review the root agent

## Error Handling

- If `agent-blueprint.yaml` is missing: prompt the developer to run
  /catalyst.blueprint first
- If `agents-cli` is not installed: display installation instructions
- If YAML validation fails: display specific validation errors and
  the field(s) that need fixing
- If Garden template clone fails: check network connectivity and
  agents-cli installation
- If skill installation fails provenance check: display the mismatched
  SHA and warn that the skill may have been tampered with
```

---

### memory/adk-reference.md

```markdown
---
role: reference
description: Google ADK class reference for agent development
source: Google ADK documentation (public)
---

# ADK Agent Classes — Quick Reference

## Agent Types

| Class | When to use | Key parameters |
|---|---|---|
| `LlmAgent` | Single reasoning agent with tools. Also used as root Coordinator. | `name`, `model`, `tools`, `sub_agents`, `system_instruction` |
| `SequentialAgent` | Ordered pipeline — each step receives output of previous. | `name`, `sub_agents` (executed in order) |
| `ParallelAgent` | Concurrent execution — independent tasks run simultaneously. | `name`, `sub_agents` (executed in parallel) |
| `LoopAgent` | Iterative refinement — repeats until exit condition or max iterations. | `name`, `sub_agents`, `max_iterations` |

## Tool Types

| Class | When to use | Key parameters |
|---|---|---|
| `FunctionTool` | Wrap a Python function as an agent tool. | `func` (the Python function) |
| `MCPToolset` | Connect to an MCP server for external tool access. | `connection_params` (endpoint, transport, auth) |
| `AgentTool` | Connect to an external A2A agent. | `agent` (endpoint, auth, timeout) |
| `SkillToolset` | Load and use installed skills with progressive disclosure. | `skill_path`, includes `load_skill_resource` |
| `LongRunningFunctionTool` | Async human approval — pauses execution until human responds. | `func` (returns pending, resumes on callback) |

## Common Imports

```python
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
from google.adk.tools import FunctionTool, MCPToolset, AgentTool, SkillToolset
from google.adk.tools import LongRunningFunctionTool
```

## Session and Memory

- `InMemorySessionService` — development/testing only
- `FirestoreSessionService` — production session persistence
- `SpannerSessionService` — high-scale session persistence
- Memory and artifacts configured via Cloud Run environment variables
```

---

### memory/company-patterns.md

```markdown
---
role: reference
description: Company coding standards for agent development
source: Enterprise Architecture team
---

# Company Agent Development Standards

## Naming Conventions

- Agent names: `snake_case` (e.g., `intake_pipeline`, `enrichment_fan_out`)
- Tool names: `kebab-case` (e.g., `bigquery-policy`, `cloud-sql-claims`)
- Project names: `kebab-case` (e.g., `fnol-coordinator`, `loan-origination`)
- File names: `snake_case.py` matching the agent/tool name

## Project Structure

All agent projects MUST follow this folder structure:

```
{project-name}/
├── app/
│   ├── agent.py                  ← Root agent
│   ├── sub_agents/               ← One file per sub-agent
│   ├── mcp_connections/          ← One file per MCP server
│   ├── a2a_clients/              ← One file per A2A agent
│   ├── tools/                    ← One file per FunctionTool
│   ├── callbacks/                ← Model Armor + tool callbacks
│   └── skills/                   ← Installed skills
├── deployment/terraform/         ← Infrastructure as code
├── observability/                ← Dynatrace + OTel config
├── ci-cd/                        ← Pipeline definitions
├── pyproject.toml
├── README.md
└── agent-blueprint.yaml          ← The blueprint that generated this project
```

## Code Standards

- Every generated file includes a header comment:
  `# GENERATED by agents-cli — DO NOT EDIT MANUALLY`
- FunctionTool implementations include (when business rules authored in spec):
  `raise NotImplementedError("Engineer must implement")`
- System prompt placeholders marked: `<<< ENGINEER MUST WRITE >>>`
- Zero hardcoded credentials — all secrets via Secret Manager
- All MCP connections specify transport and auth explicitly
- All A2A connections have 30-second timeout default
```

---

### memory/approved-tools.md

```markdown
---
role: reference
description: Company-approved MCP servers and A2A agents
source: Platform Engineering team
updated: 2026-05-01
---

# Approved Tools Registry

## MCP Servers (approved for production use)

| Name | Endpoint | Transport | Auth | Owner |
|---|---|---|---|---|
| bigquery-mcp | bigquery.googleapis.com | sse | workload_identity | GCP Managed |
| cloud-sql-mcp | cloudsql-mcp.internal:8080 | sse | workload_identity | Platform Eng |
| vertex-search-mcp | vertexai-search.googleapis.com | sse | workload_identity | GCP Managed |
| gcs-mcp | storage.googleapis.com | sse | workload_identity | GCP Managed |
| weather-api-mcp | weather-api.internal:8080 | sse | api_key | Data Eng |

## A2A Agents (approved for production use)

| Name | Endpoint | Auth | Owner | Domain |
|---|---|---|---|---|
| body-shop-network | https://bodyshop.partner.com/a2a | spiffe | Partner | Insurance |
| rental-car-service | https://rental.partner.com/a2a | spiffe | Partner | Insurance |
| credit-bureau | https://credit.partner.com/a2a | mutual_tls | Partner | Finance |

## Requesting New Tools

To request a new MCP server or A2A agent be added to the approved list:
1. Open a request in the Platform Engineering JIRA project
2. Provide: tool name, endpoint, auth method, owner, and business justification
3. Platform Engineering will validate the endpoint, security posture, and SLA
4. Upon approval, the tool is added to this list and to Apigee API Hub
```

---

### memory/infra-standards.md

```markdown
---
role: reference
description: Company Terraform module and infrastructure standards
source: Platform Engineering team
updated: 2026-05-01
---

# Infrastructure Standards

## Terraform Module Registry

All agent infrastructure MUST use company-approved Terraform modules.
Do NOT write raw Terraform resources — use module references.

| Module | Source | Current Version | Purpose |
|---|---|---|---|
| cloud-run-agent | github.com/company/tf-modules//cloud-run-agent | v3.1.0 | Cloud Run agent service provisioning |
| cloud-sql | github.com/company/tf-modules//cloud-sql | v2.4.0 | Cloud SQL instances |
| vpc-sc | github.com/company/tf-modules//vpc-sc | v1.8.0 | VPC Service Controls perimeter |
| cmek | github.com/company/tf-modules//cmek | v1.2.0 | KMS key ring + crypto keys |
| secret-manager | github.com/company/tf-modules//secret-manager | v1.5.0 | Secret storage |
| apigee-proxy | github.com/company/tf-modules//apigee-proxy | v2.1.0 | API gateway proxy |

## Version Pinning Rules

- Always pin to exact version tags (e.g., `v3.1.0`), never `latest` or branch refs
- Version updates require PR approval from Platform Engineering
- Major version bumps require EA review

## CI/CD Templates

| Tool | Template | Version | Purpose |
|---|---|---|---|
| Jenkins | agent-infra-plan-apply-v3 | v3 | Terraform plan + apply with OPA checks |
| Harness | agent-deploy-canary-v4 | v4 | Canary deployment with progressive rollout |

## Security Defaults

- CMEK: required for all production agents
- VPC-SC: required for all production agents
- Model Armor: enabled by default
- DLP: enabled by default for agents handling PII
- Service accounts: one per agent, least privilege, no key export
```

---

## Related Documents

| Document | Audience | What it covers | When to consult |
|---|---|---|---|
| **AgentCatalyst agents-cli Architecture Document** | Architects, tech leads | WHY — architectural decisions, Blueprint Advisor MCP Server (3 tools: recommend/validate/assemble), FORBIDDEN 3-layer enforcement, MCP Server security (OAuth 2.0, TLS 1.3), rate limiting (10 calls/hr), versioning, offline fallback, golden dataset quality gate, cost model (48× ROI) | When you need to understand why something is designed the way it is |
| **This Developer Guide** | Developers | HOW — greenfield FNOL walkthrough, spec writing, business logic capture, EvalOps (no `agents-cli eval`), FORBIDDEN commands, troubleshooting | When you need to build something |
| **AgentCatalyst Operations Runbook** | Platform engineering | PROCEDURES — wire-level Vertex AI Search APIs, transport security, search quality regression, acceptance telemetry, catalog backup/DR (RTO < 4 hrs), failure modes, MCP Server ops | When you need to debug platform issues or escalate |

### Key cross-references

| This guide section | Architecture doc section | Why you might need it |
|---|---|---|
| Section 2 (Greenfield FNOL) | End-to-end thread | Narrative context for walkthrough steps |
| Section 4 (Writing Specs) | Layer 2 — 11 agentic patterns | Full pattern list and selection signals |
| Section 4a (Business Logic) | Layer 1 — spec template table | How each spec section impacts code generation |
| Section 4b (EvalOps) | Layer 4 — EvalOps + golden dataset quality gate | Full 3-layer architecture. `agents-cli eval` FORBIDDEN. |
| Section 5 (YAML Blueprint) | Layer 2 — MCP Server (3 tools, security, rate limiting) | How the YAML is created. Offline fallback if server down. |
| Section 7 (Troubleshooting) | → Operations Runbook, Section 6 + 9 | Platform failure modes, escalation matrix, MCP Server ops |
| Section 11 (Deployment Rules) | Layer 3 — FORBIDDEN 3-layer enforcement | Why eval/simulate/deploy are blocked at 3 layers |
| Section 12 (Deployment Scenario) | Layer 4 — Jenkins + Harness architecture | Full CI/CD architecture with 3-phase EvalOps |

*The architecture document provides the WHY. This guide provides the HOW. The operations runbook provides the PROCEDURES.*
