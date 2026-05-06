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
/catalyst.blueprint   # Blueprint Advisor returns app-blueprint.yaml
# review + edit the YAML
/catalyst.generate    # coding agent generates everything using skills
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
| Blueprint Advisor | Agent Runtime (GCP) | The AI that reads your spec and recommends an architecture |
| Approved tools registry | Apigee API Hub + `memory/approved-tools.md` | What MCP servers, APIs, and A2A agents you can connect to |
| Company Terraform modules | `github.com/company/tf-modules` | Pre-approved infrastructure modules |

### What you (the developer) do

| Step | What you do | Time |
|---|---|---|
| 1 | Install the preset + skills (one-time) | 5 min |
| 2 | `/specify` — describe your problem in structured English | 15 min |
| 3 | `/plan` — answer technical questions | 5 min |
| 4 | `/catalyst.blueprint` — get AI architecture advice | 30 sec (wait) |
| 5 | Review and edit the YAML | 10 min |
| 6 | `/catalyst.generate` — coding agent generates the project | 5–10 min |
| 7 | Write business logic + system prompts (the 20%) | 2–4 hours |
| 8 | Commit, PR, CI/CD | Standard process |

---

## 1. Prerequisites

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

### 2.5 `/catalyst.blueprint` — Get AI advice

Type `/catalyst.blueprint`. Wait ~30 seconds. `app-blueprint.yaml` appears in your workspace.

The coding agent shows a summary:

```
Blueprint Advisor recommends:
  5 agents: LlmAgent (coordinator), SequentialAgent (intake),
            ParallelAgent (enrichment), LoopAgent (summary), LlmAgent (HITL)
  3 MCP servers: bigquery-policy, cloud-sql-claims, vertex-search-policies
  3 A2A agents: body-shop-network, rental-car-service, police-report-service
  3 FunctionTool stubs: severity_classifier, coverage_calculator, notification_sender
  2 skills: bigquery v1.2.0, fraud-detection v2.0.1

Review the YAML and edit before running /catalyst.generate.
```

### 2.6 Review and edit the YAML

Open `app-blueprint.yaml`. Common edits:

| What to check | Fix if wrong |
|---|---|
| Agent types | Change `type: SequentialAgent` to `type: ParallelAgent` |
| Tool assignment | Change `assigned_to: extract_details` to `assigned_to: fnol_coordinator` |
| Missing tool | Add entry to `tools.mcp_servers:` (check `memory/approved-tools.md`) |
| Model | Change `platform.model:` |

### 2.7 `/tasks` — See the breakdown

Type `/tasks`. See the 80/20 split:

**Auto-generated:** Agent classes, MCP connections, A2A clients, Model Armor callbacks, Terraform, Dynatrace, CI/CD pipelines

**You implement:** System prompts, `severity_classifier()`, `coverage_calculator()`, `notification_sender()`, test data

### 2.8 `/catalyst.generate` — Generate everything

Type `/catalyst.generate`. The coding agent reads the YAML and uses installed skills to generate the project:

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
│   ├── main.tf                           ← Company TF modules
│   ├── variables.tf
│   └── terraform.tfvars
├── observability/
│   ├── dynatrace/
│   └── otel/
├── ci-cd/
│   ├── Jenkinsfile                       ← Company template ref
│   └── harness-pipeline.yaml             ← Canary deployment
├── pyproject.toml
├── README.md
└── app-blueprint.yaml
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

**Terraform module** (guided by `company-terraform-patterns` skill):

```hcl
# deployment/terraform/main.tf
module "agent-runtime" {
  source  = "github.com/company/tf-modules//agent-runtime?ref=v3.1.0"
  project = var.gcp_project
  region  = var.gcp_region
  agent_name = "fnol-coordinator"
}
```

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

**Key language:** Notice the repeated "EXISTING" and "DO NOT create new" signals. This tells the Blueprint Advisor and the coding agent to work within the existing infrastructure, not generate new infrastructure.

#### Step 3: `/plan` — Technical decisions

```
Runtime:           ecs_fargate (EXISTING)
Backend framework: Spring Boot 3.x (EXISTING build.gradle)
Frontend framework: Angular 17+ (EXISTING angular.json)
Database:          Oracle RDS (EXISTING — use boilerplate/application.yml)
Terraform:         SKIP — infrastructure already exists
CI/CD:             EXISTING Jenkinsfile + harness-pipeline.yaml
```

#### Step 4: `/catalyst.blueprint` — Get AI advice

The Blueprint Advisor reads the spec and recognizes the brownfield signals. It returns `app-blueprint.yaml` that references existing infrastructure rather than creating new infrastructure:

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

#### Step 5: Review the YAML

Verify:
- `database.config_source` points to the correct `application.yml`
- Entity fields match your Oracle column types
- Frontend proxy references the existing `proxy.conf.json`
- Infrastructure is marked SKIP

#### Step 6: `/catalyst.generate` — Generate the application code

Type `/catalyst.generate`. The coding agent reads the YAML and uses skills to generate **only the application code** — no infrastructure, no CI/CD, no Docker configs (those already exist):

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

### Words that help pattern selection (agentic)

| What you write | What the Blueprint Advisor infers |
|---|---|
| "First... Then... After that" | Sequential pipeline (SequentialAgent) |
| "Simultaneously" / "In parallel" | Parallel fan-out (ParallelAgent) |
| "Generate... validate... refine until" | Loop (LoopAgent) |
| "If [condition], route to [human]" | Human-in-the-loop |
| "they operate their own" | External A2A agent connection |
| "our proprietary" | FunctionTool stub (you implement) |

### Words that help brownfield detection

| What you write | What the coding agent does |
|---|---|
| "EXISTING REST API" | Generates FunctionTool wrapper, not new service |
| "DO NOT create new" | Skips infrastructure generation |
| "EXISTING database" | Uses existing connection config, doesn't generate new DB |
| "Use the existing" | References existing files (symlinks or imports) |
| "MUST NOT modify" | Preserves existing code, generates alongside it |

### Common mistakes

| Mistake | Better approach |
|---|---|
| "uses BigQuery" (no workload type) | "BigQuery (analytical queries, read-only)" |
| "body shop API" (no ownership) | "body shop — they operate their own API" |
| "process the claim" (vague workflow) | Break into explicit steps with ordering words |
| One spec for multiple apps | One spec per application. Multiple apps = multiple specs. |

---

## 5. Understanding the YAML Blueprint

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

### Brownfield signals in the YAML

```yaml
infrastructure:
  terraform:
    action: SKIP              # Don't generate Terraform
  cicd:
    action: SKIP              # Don't generate CI/CD
database:
  config_source: boilerplate/backend/src/main/resources/application.yml  # Use EXISTING config
```

---

## 6. Re-generating — Iterating on the Design

You can change the YAML and re-run `/catalyst.generate` as many times as needed.

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

Files marked `<<< ENGINEER MUST WRITE >>>` or `raise NotImplementedError` are stubs. If you've already implemented them and re-generate, the generated version will overwrite your implementation. **Always commit before re-generating.**

---

## 7. Writing Tests for Generated Code

### Agentic: Agent evaluation datasets

For agents, create evaluation datasets that test the agent's tool-calling behavior:

```json
// tests/evalsets/fnol-basic.json
[
  {
    "input": "I was in a car accident on I-85. My policy number is P-12345.",
    "expected_tool_calls": ["bigquery-policy"],
    "expected_agent_sequence": ["verify_policy", "extract_details"],
    "expected_output_contains": ["policy verified", "incident details"]
  },
  {
    "input": "The damage is about $30,000 and there were injuries.",
    "expected_tool_calls": ["severity_classifier"],
    "expected_output_contains": ["high severity"],
    "expected_routing": "adjuster_review"
  }
]
```

Run evaluation locally with the Gen AI Evaluation Service (GA):

```python
from vertexai.evaluation import EvalTask
eval_task = EvalTask(dataset="tests/evalsets/fnol-basic.json", metrics=["tool_trajectory", "response_quality"])
result = eval_task.evaluate(model="gemini-2.0-flash")
```

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

## 8. Deployment Rules — What NOT to Do

| ❌ Never do this | ✅ Do this instead |
|---|---|
| Deploy directly from your machine | Commit → PR → Jenkins → Harness |
| Run `agents-cli deploy` (if installed) | Company-cicd skill generates pipeline files instead |
| Generate Cloud Build config | Company uses Jenkins |
| Provision GCP/AWS resources manually | Jenkins runs Terraform after PR merge |

The `company-cicd` skill explicitly tells the coding agent: "Generate pipeline files. Do not deploy directly." Three override layers (skill + GEMINI.md + command) reinforce this.

---

## 9. Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `/catalyst.blueprint` returns error | Blueprint Advisor API unreachable | Check `CATALYST_BLUEPRINT_API` env var |
| YAML validation fails | Schema error | Common: missing `assigned_to`, unpinned version, invalid type |
| Skill provenance check fails | Skill updated since YAML generated | Update `version:` in YAML |
| Skills not visible | Not installed | Run `gemini skills install github.com/company/agentcatalyst-skills --scope user` |
| Coding agent tries to deploy directly | Default workflow overriding company rules | Verify skills installed, check GEMINI.md has override table |
| Brownfield generates new infrastructure | Spec missing "EXISTING" / "DO NOT create" signals | Add explicit brownfield language to spec (see Section 4) |
| Generated code doesn't compile | Skill version mismatch | Check ADK/Spring Boot version matches skill expectations |
| Oracle connection fails locally | Wrong JDBC URL or missing credentials | Check `application.yml` datasource config, ensure Oracle RDS is accessible from your machine |

### Getting help

| Channel | When |
|---|---|
| `#agentcatalyst` Slack | General questions, peer help |
| Platform Engineering JIRA | Bugs, new skill/tool requests |
| EA office hours | Pattern questions, spec reviews, architecture guidance |

---

## 10. Reference — All Commands

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

## 11. Preset File Map

Every file in the `.specify/` folder serves a specific purpose:

```
.specify/
├── preset.yml                    ← Manifest: archetype, templates, commands, settings
│
├── templates/
│   ├── spec-template.md          ← /specify loads this — archetype-specific sections
│   │                                with coaching prompts and examples
│   ├── plan-template.md          ← /plan loads this — technical questions
│   │                                mapping to YAML blueprint fields
│   └── tasks-template.md        ← /tasks loads this — generated vs
│                                    engineer-implements breakdown
│
├── commands/
│   ├── catalyst.blueprint.md    ← /catalyst.blueprint — instructions for
│   │                                the coding agent to call Blueprint
│   │                                Advisor API and save YAML
│   └── catalyst.generate.md     ← /catalyst.generate — skill activation
│                                    sequence with CRITICAL override:
│                                    DO NOT deploy directly
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

## 12. FAQ

**Q: Can I write the YAML manually?**
A: Yes. The coding agent doesn't care who produced the YAML. Write it by hand, copy from a teammate, or use any tool.

**Q: Can I use different coding agents for different steps?**
A: Yes. `/specify` in Copilot, `/catalyst.generate` in Claude Code — the preset files are the same.

**Q: What if my pattern doesn't have a ref impl (like the SPA pattern)?**
A: That's exactly the scenario in Section 3. Use AgentCatalyst to generate the application code on top of the existing IaC and boilerplate. The coding agent's skills teach it how to write correct Spring Boot / Angular / ADK code that plugs into the existing infrastructure.

**Q: Can I use AgentCatalyst for non-GCP infrastructure (AWS, Azure)?**
A: For the agentic archetype, GCP is required (Agent Runtime is GCP-only). For microservice/pipeline/API archetypes, the application code is cloud-agnostic — only the company overlay skills (Terraform, CI/CD) are cloud-specific. The SPA brownfield example uses ECS Fargate (AWS).

**Q: Why not just use a project template (like Spring Initializr)?**
A: Templates give you a blank starter. AgentCatalyst gives you a starter that's already wired to your specific database, your specific APIs, your specific infrastructure, following your company's specific patterns. The Blueprint Advisor reads your spec and generates a YAML that's custom to your use case — not a generic template.

**Q: Is the generated code production-ready?**
A: The boilerplate is production-ready — correct framework patterns, proper project structure, company-standard infrastructure. You add: business logic, system prompts (for agents), test data, and domain-specific validation. That's the 20%.

**Q: How does this work with existing IaC that uses AWS (not GCP)?**
A: The brownfield SPA example in Section 3 uses AWS (ECS Fargate + Oracle RDS). AgentCatalyst generates the application code — it doesn't care about the cloud provider for the infrastructure. The `infrastructure.terraform.action: SKIP` flag tells it to leave existing infrastructure untouched. The company overlay skills for CI/CD would reference Jenkins/Harness templates appropriate for AWS deployment.
