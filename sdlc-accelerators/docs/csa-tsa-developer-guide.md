# SDLC Accelerators Brownfield — Developer Guide

*Get from "I need to modernize this legacy app" to a production-ready target-state blueprint plus generated BFF code, IaC, and CI/CD pipelines in under one working day.*

*Canonical name: **SDLC Accelerators Brownfield**. Preset: `sdlc-accelerators-brownfield`.*

---

### Document set

| Document | Filename | Covers |
|---|---|---|
| Architecture | `csa-tsa-speckit-architecture.md` | **WHY** — design decisions, Solution Accelerator internals, peripheral systems |
| **This document** | `csa-tsa-speckit-developerguide.md` | **HOW** — step-by-step workflow, templates, examples |
| Operating Playbook | `csa-tsa-speckit-operating-playbook.md` | **PROCEDURES** — operations, governance, onboarding |

### Related core SDLC Accelerators documents

| Core document | Filename | Consult for |
|---|---|---|
| Core Developer Guide | `sdlc-accelerators-archetype-agnostic-developer-guide.md` | Greenfield workflows (§2–§3), spec signal words (§4), app-blueprint.md schema (§5), confidence scores (§8), troubleshooting (appendix) |
| Core Architecture | `sdlc-accelerators-architecture-archetype-agnostic.md` | Base Solution Accelerator MCP design (Layer 2), OAuth 2.1 + Entra ID authentication (Layer 2 Security), IaC generation via GitHub MCP Server (Layer 3), EvalOps three-layer lifecycle (Layer 4) |
| Core Operations Runbook | `csa-tsa-speckit-operating-playbook.md` | OAuth 2.1 / Entra ID troubleshooting (§9), Governance Guardian operations (§10), Governance Guardian wire format (§10a), MCP tool wire format (§1a) |
| Governance Guardian Extension | `governance-guardian-architecture.md` | `/accelerator.assess` design, assessment flow, scorecard format, `recordTechDebt` gate, tech debt registry |
| app-blueprint.md Template | `app-blueprint-md-template-and-fnol-example.md` | 12-section template structure, FNOL reference example, workspace file layout |

---

## Table of Contents

1. [Quick Start](#1-quick-start-tldr)
2. [Prerequisites](#2-prerequisites)
3. [One-Time Setup](#3-one-time-setup)
4. [Workflow Overview](#4-workflow-overview)
5. [`/speckit.constitution` — Versioned Dual Constitution](#5-speckitconstitution--versioned-dual-constitution)
6. [`/accelerator.epic-to-spec` — Fuse the Epic with the CSA](#6-acceleratorepic-to-spec--fuse-the-epic-with-the-csa)
7. [Spec Template (full)](#7-spec-template-full)
8. [Worked Example: `spec.md`](#8-worked-example-specmd)
9. [`/speckit.plan.draft` + `/speckit.plan.review`](#9-speckitplandraft--speckitplanreview)
10. [Plan Template (full)](#10-plan-template-full)
11. [Worked Example: `plan.md`](#11-worked-example-planmd)
12. [`/accelerator.blueprint`](#12-acceleratorblueprint)
13. [Reviewing the Blueprint and Design Contract](#13-reviewing-the-blueprint-and-design-contract)
14. [`/accelerator.generate`](#14-acceleratorgenerate)
15. [`/accelerator.refresh` — Keeping Contracts Alive](#15-acceleratorrefresh--keeping-contracts-alive)
16. [Custom Agent & Prompt Files](#16-custom-agent--prompt-files)
17. [Quality Self-Checks](#17-quality-self-checks)
18. [Common Failure Modes & Fixes](#18-common-failure-modes--fixes)
19. [FAQ](#19-faq)

### How Migration Readiness Validation Works (Two Layers)

Brownfield validation runs at two layers. This is MORE critical than greenfield because errors affect a running production system with real users and real data.

**Layer 1 — Local (during `/accelerator.epic-to-spec` fusion, or the `/speckit.specify` fallback):** As the CSA-sourced integration blocks are composed (or the `csa-extractor` pre-fills them in the fallback), the preset validates EACH integration. You'll see real-time feedback per integration:

```
Agent: "The CSA extractor found 15 integrations. Let's validate each one."
Agent: "Integration: claims-database. What technology and version?"
You: "Some legacy database"
Agent: ❌ I need the specific technology. Is it Oracle, PostgreSQL, DB2?
       The Tech Substitution Table needs exact tech names to map CSA→TSA.
You: "Oracle 19c"
Agent: ✅ Oracle 19c → maps to Aurora PostgreSQL (confidence: 0.90).

Agent: "Data flow direction for claims-database?"
You: "Both ways"
Agent: ✅ Bidirectional — this will need dual-write coexistence in Phase 2.
       "What coexistence mode? dual-read, dual-write, hard-cutover?"
You: "dual-write"
Agent: ✅ Flagged: dual-write during Phase 2. Rollback = stop writes to new system.
```

**Layer 2 — Server-side (inside `blueprint_start`):** When you run `/accelerator.blueprint`, the Solution Accelerator MCP Server delegates blueprint reasoning to the **Solution Accelerator Agent** (one ADK agent; its `recommend_architecture` FunctionTool) and runs `validate_spec` as Step 0 with access to the Tech Substitution Table (are ALL tech mappings approved?), Apigee API Hub (are A2A agents actually deployed?), ADR Store (do migration decisions comply with architecture decisions?), and cross-integration graph analysis (circular dependencies? conflicting coexistence constraints?).

**Why both layers:** Layer 1 catches missing tech names, unclassified integrations, and missing coexistence flags DURING capture — you fix each one in real time. Layer 2 catches cross-integration conflicts and verifies against live data sources. Without Layer 1, you'd discover that 5 of your 15 integrations are missing coexistence flags only AFTER waiting for the Solution Accelerator to process — and the resulting blueprint would have data loss risks built in.

### Writing Brownfield Specs That Pass Migration Readiness Validation

The Solution Accelerator validates your spec for **migration readiness** before running the RAG pipeline. Brownfield validation is different from greenfield — it checks whether you have enough information to plan a SAFE migration, not just a correct architecture.

**CSA Completeness — Name specific technologies with versions (BLOCK if missing):**
- ✅ GOOD: "Oracle 19c (claims database), IBM MQ 9.3 (async messaging), Tomcat 8.5 + JSP (frontend), F5 BIG-IP (load balancer)"
- ❌ BAD: "Legacy database, some messaging, old web frontend"
- WHY: The Tech Substitution Table needs exact tech names to find approved CSA→TSA mappings. "Legacy database" has no mapping; "Oracle 19c" maps to "Aurora PostgreSQL (confidence 0.90)".

**Integration Type Classification — Classify every integration (BLOCK if <50%):**
- ✅ GOOD: "policy-lookup: synchronous REST API. claims-queue: async IBM MQ. nightly-recon: batch PL/SQL job. reinsurer-feed: file transfer (CSV via SFTP)."
- ❌ BAD: "policy-lookup connects to claims-queue somehow"
- WHY: Each type needs a different migration approach. Sync APIs → Strangler-Fig proxy. Async → message bridge. Batch → scheduled job migration. DB links → data migration scripts.

**Data Flow Direction — Mark read/write/bidirectional (BLOCK if <50%):**
- ✅ GOOD: "policy-lookup: **read-only**. claims-db: **bidirectional** (agents read and write). payment-gateway: **write-only**."
- ❌ BAD: "Data goes back and forth between systems"
- WHY: Read-only integrations go to Phase 1 (safest — proxy routes reads to new system). Write-only and bidirectional go to Phase 2 (needs dual-write coexistence). This determines migration phase assignment.

**Criticality Rating — Rate every integration (WARN if <50%):**
- ✅ GOOD: "claims-db: **critical** (zero-downtime required, <5 min rollback). policy-lookup: **high**. dashboard-api: **low**."
- ❌ BAD: "Everything is important"
- WHY: Migration ORDER: low-risk first (build confidence), critical last (after patterns proven). Critical integrations need verified rollback procedures before migration starts.

**Coexistence Constraints — Flag every integration (BLOCK if zero flags):**
- ✅ GOOD: "claims-db: **dual-write** (both old and new must receive writes during Phase 2). policy-lookup: **dual-read** (both must return same data during Phase 1). auth-ldap: **hard-cutover** (switch all at once, rollback = revert DNS)."
- ❌ BAD: No coexistence information provided
- WHY: This is the #1 brownfield risk. Missing dual-write flags → data inconsistency during migration. Data written to the new system but not the old (or vice versa) creates split-brain scenarios that are extremely difficult to recover from.

**API Surface — Document external API contracts (WARN if missing):**
- ✅ GOOD: "payment-gateway: OpenAPI spec at /docs/payment-api-v2.yaml, consumed by billing-system and reinsurer-portal. Must maintain backward compatibility."
- ❌ BAD: "Payment API exists but no one documented it"
- WHY: The Strangler-Fig proxy routes existing API calls to the new system. Without documented contracts, the proxy can't be configured correctly → external consumers break during migration.

---


> **Implementation status:** The brownfield archetype is implemented under `brownfield/` (spec/plan
> parsing, the 8-signal `validate_spec` gate, all four tools, the design contract v2.0, migration code
> generation, and the vSphere MPA → AWS SPA reference case). See the Architecture doc's *Implementation
> Status* section. Tool 2 (`recommend_architecture`) and the live-service calls are seams; the
> decision-table rows and ADR predicates are human-authored.

## 1. Quick Start (TL;DR)

```bash
# 1. Install preset (one-time)
specify preset add sdlc-accelerators-brownfield

# 2. Initialize in your legacy app's repo
cd /path/to/legacy-app-repo
specify init --here --preset sdlc-accelerators-brownfield --integration copilot

# 3. In VSCode, Agent mode, Claude Opus 4.6:
/speckit.constitution       # confirm enterprise principles (one-time per project)
/accelerator.epic-to-spec   # FRONT DOOR — fuse Rally Epic + CSA architecture.md → spec.md
# /speckit.specify          # no-Epic fallback: diagram extraction → spec.md → elicitation
/speckit.plan.draft         # first-pass r-factor + cutover per integration
/speckit.plan.review        # async EA/architect review of the plan
/accelerator.blueprint         # async: start → poll (progress in chat) → retrieve blueprint + contract
# review blueprint, contract, diagrams
/accelerator.assess            # governance assessment → scorecard + findings (fix showstoppers → re-assess)
/accelerator.generate          # governance gate (recordTechDebt → stop/resume) + brownfield-aware code + IaC

# Later (before every PR if contract is stale):
/accelerator.refresh           # re-run advisor, diff contract, return to LIVE
```

---

## 2. Prerequisites

→ *Architecture §2 covers the Spec Kit framework relationship and version governance.*

### 2.1 Workstation requirements

| Tool | Version | Install |
|---|---|---|
| VSCode | Latest | https://code.visualstudio.com |
| GitHub Copilot extension | Latest | Marketplace — Pro+, Business, or Enterprise; Opus 4.6 entitlement |
| Python | 3.10+ | `brew install python` |
| `uv` | Latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `specify` CLI | Pinned (see preset.yml) | `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@<pinned-version>` |
| `gh` CLI | Latest | `brew install gh` |
| `gcloud` CLI | Latest | `brew install google-cloud-sdk` |
| AWS CLI | Latest | `brew install awscli` |

### 2.2 Copilot model setup

The preset prompt files declare `model: ['Claude Opus 4.6', 'Claude Opus 4.7', 'Claude Sonnet 4.6']`. This fallback chain handles the model-entitlement fluctuation observed across Copilot plans in 2026. If your tenant is Business/Enterprise, confirm your admin has enabled the Opus 4.6 policy. Quality degrades ~5% at Sonnet 4.6 level for the diagram extraction task; spec elicitation is unaffected.

→ *Operating Playbook §9 covers model availability monitoring and communication.*

---

## 3. One-Time Setup

```bash
gh auth login
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.5.2
gcloud auth login && gcloud config set project YOUR_GCP_PROJECT
gemini skills install github.com/company/sdlc-accelerators-skills --scope user
```

### Per-project initialization

```bash
cd /path/to/legacy-app-repo
specify init --here --preset sdlc-accelerators-brownfield --integration copilot
```

This drops the following into your repo:

```
.specify/
├── preset.yml                           ← manifest (pinned speckit_version)
├── templates/
│   ├── spec-template.md                 ← brownfield CSA-inventory template
│   ├── plan-template.md                 ← r-factor + sequencing template
│   └── tasks-template.md
├── memory/
│   ├── approved-tools.md
│   ├── tech-substitution-cache.md       ← local hint cache (refreshed weekly)
│   └── infra-standards.md
└── scripts/
    └── package_blueprint_request.py

.github/
├── prompts/
│   ├── speckit.constitution.prompt.md
│   ├── speckit.specify.prompt.md        ← diagram extraction + spec authoring
│   ├── speckit.plan.draft.prompt.md     ← developer first-pass
│   ├── speckit.plan.review.prompt.md    ← async EA/architect review
│   ├── accelerator.blueprint.prompt.md
│   ├── accelerator.assess.prompt.md
│   ├── accelerator.generate.prompt.md
│   └── accelerator.refresh.prompt.md
├── agents/
│   └── csa-extractor.agent.md           ← diagram extractor agent
├── instructions/
│   └── csa-tsa-conventions.instructions.md
└── copilot-instructions.md

memory/
├── constitution-enterprise.md           ← read-only, versioned with preset
└── constitution-project.md              ← editable, validated against enterprise
```

Verify: in Copilot Chat, Agent mode, type `/` and confirm `speckit.constitution`, `speckit.specify`, `speckit.plan.draft`, `speckit.plan.review`, `accelerator.blueprint`, `accelerator.assess`, `accelerator.generate`, `accelerator.refresh` all appear.

---

## 4. Workflow Overview

![SDLC Accelerators Brownfield — Detailed Component Architecture](sdlc-accelerators-brownfield-architecture_detailed.png)

| Step | Command | What happens | Time |
|---|---|---|---|
| 0 | CSA Agent (upstream, separate system) | Reverse-engineer the legacy app → CSA diagram **+ `architecture.md`** in your workspace | — |
| 1 | BA / Solution Architect | Author a Rally Epic with a **Modernization Scope** table (per-component Refactor/Rehost + AWS target) | — |
| 2 | `/accelerator.epic-to-spec <EpicID>` | **Front door** — fuse the Epic with the CSA `architecture.md` → canonical `spec.md` + `modernization-scope-ledger.json`. **Replaces `/speckit.specify`.** | 2 min |
| 2-alt | `/speckit.specify` | **No-Epic fallback** — csa-extractor parses the diagram → pre-fills spec.md → elicits details | 30 min |
| 3 | `/speckit.constitution` | Confirm enterprise principles (one-time per project) | 5 min |
| 3 | `/speckit.plan.draft` | Developer first-pass: r-factor + cutover per integration | 30 min |
| 4 | `/speckit.plan.review` | Async EA/architect review with structured comments | 1–3 days |
| 5 | `/accelerator.blueprint` | Async: start → poll (progress in chat) → retrieve | 1–30 min |
| 6 | Review | Review blueprint, contract, diagrams | 30 min |
| 6a | `/accelerator.assess` | Governance assessment → scorecard + findings (iterative) | 1–5 min |
| 7 | `/accelerator.generate` | Governance gate + brownfield-aware skills generate code + IaC + pipelines | 5–10 min |
| 8 | Developer work | Review, refine, business logic, tests, commit | 2–4 hours |
| 9 | `/accelerator.refresh` (if needed) | Re-verify contract freshness before PR/deploy | 2 min |

The plan review step (4) is async — you don't block waiting. Continue with other work or other integrations. The reviewer leaves comments; you resolve them before step 5.

→ *Architecture §6 covers the 10-stage flow from the architectural perspective.*

---

## 5. `/speckit.constitution` — Versioned Dual Constitution

→ *Architecture doc Part II §10 covers the versioning model. Operating Playbook §2.6 covers enterprise constitution governance.*

Run once per project:

```
/speckit.constitution
```

SDLC Accelerators Brownfield uses a **dual-file constitution**:

- **`constitution-enterprise.md`** — read-only, shipped by the preset, updated only via `specify preset upgrade`. Carries the enterprise version tag (e.g. `v2026Q2`). You cannot edit this file; it is the baseline.
- **`constitution-project.md`** — you edit this to add project-specific principles (e.g. "this project must not use any AWS services outside us-east-1").

A pre-commit hook validates that `constitution-project.md` does not contradict `constitution-enterprise.md`. If it does, the commit is blocked with a specific error.

Enterprise non-negotiables in the current version:

1. Never invent tech substitutions — every mapping must come from the Tech Substitution Table or an explicit waiver.
2. Cross-cloud transit must be mTLS or PrivateLink — no public-internet OAuth-only paths.
3. Dual-publish windows require documented downstream idempotency confirmation.
4. APIC and IBM MQ are sunset technologies — replatform/refactor only.
5. Generated IaC must reference company `tf-modules` — no bespoke Terraform.

---

## 6. `/accelerator.epic-to-spec` — Fuse the Epic with the CSA

→ *Architecture §7 covers the CSA Agent handoff boundary and the architecture.md contract. Architecture §9 "Epic-to-Spec Fusion" covers the internals.*

This is the brownfield **front door**. It fuses a Rally Epic's modernization intent with the upstream CSA and emits the **final** `spec.md` — you do **not** run `/speckit.specify` (it remains a no-Epic fallback, §6.7). From the produced `spec.md`, `/speckit.plan.draft` follows directly.

### 6.1 Before you run it

Confirm two things are in your workspace, both produced by the upstream CSA Agent (a separate system):

1. A CSA **diagram** (`.drawio.xml` or Mermaid), and
2. A CSA **`architecture.md`** — the machine-readable current state, keyed by `CSA-COMP-XXX` components and `INT-XXX` integrations (the eight readiness signals per integration). This is the file the front door reads.

Then make sure a BA/Solution Architect has authored a Rally **Epic** whose **Modernization Scope** table declares, per CSA component, a disposition (`Refactor` | `Rehost`) and an AWS target:

```
## Modernization Scope
| Component    | Disposition | AWS Target                       | Rationale            |
|--------------|-------------|----------------------------------|----------------------|
| CSA-COMP-001 | Refactor    | ECS Fargate + Aurora PostgreSQL  | break the monolith   |
| CSA-COMP-002 | Rehost      | EC2 (lift-and-shift)             | vendor-locked adapter|
```

### 6.2 Run it

```
/accelerator.epic-to-spec E7700
```

### 6.3 What the agent does

1. **Fetch.** Retrieves the Epic by FormattedID via the Rally MCP server (client-side, Entra ID SSO — credentials stay in the IDE). Captures `ObjectVersion`.
2. **Read CSA.** Loads the workspace `architecture.md` into a component + integration registry (and computes its content hash).
3. **Resolve & cross-walk (Phase A).** Parses the Epic's Modernization Scope table and matches every named component against the CSA. Components the CSA lacks are surfaced as blocking CLARIFY items; CSA components the Epic omits are recorded as out-of-scope.
4. **Compose (Phase B).** Renders the canonical `spec.md`: a per-component modernization unit (current state → disposition → AWS target → migration considerations) for each in-scope component, plus the CSA-sourced 8-signal Integration Inventory.
5. **Gate & trace (Phase C).** Scores the spec with the same `validate_spec` readiness gate the blueprint uses, and writes `modernization-scope-ledger.json` with provenance for **both** the Epic (FormattedID + ObjectVersion) and the CSA (architecture.md hash).
6. **Write.** Saves `spec.md` + `modernization-scope-ledger.json` to your repo root.

### 6.4 Setting realistic expectations

The fusion path runs **no LLM** — same Epic + same CSA → identical `spec.md`. Quality depends on the inputs: a thin `architecture.md` (missing signals) surfaces `[NEEDS CLARIFICATION]` markers, and an Epic that scopes a component the CSA doesn't contain blocks until you fix one side. Resolve unresolved components and any unrecognized dispositions (only `Refactor`/`Rehost` are accepted) before planning.

### 6.5 Example interaction

```
You: /accelerator.epic-to-spec E7700
Agent: Fetched Epic E7700 (ObjectVersion 12). Read architecture.md (hash a1b2c3d4e5f6).
Agent: Modernization Scope: 2 components in scope.
       - CSA-COMP-001 Order Service — Refactor → ECS Fargate + Aurora PostgreSQL
       - CSA-COMP-002 Payment Gateway Adapter — Rehost → EC2 (lift-and-shift)
       Out of scope (remain as-is): CSA-COMP-003 Batch Reconciler
       Cross-walk: all scoped components resolved against the CSA. No unresolved IDs.
Agent: Composed spec.md — 2 modernization units + 3 integrations (INT-001/2/3).
       Readiness gate: score 100, not blocked.
Agent: Wrote spec.md + modernization-scope-ledger.json. Ready for /speckit.plan.draft.
```

### 6.6 When the scope can't be resolved

If the Epic names a component the CSA `architecture.md` doesn't contain, the spec marks it under `[NEEDS CLARIFICATION]` and the run is blocked: correct the `architecture.md` (return to the CSA Agent) or fix the Epic's scope table. If no Modernization Scope table is present at all, the front door falls back to the legacy extractive path and tells you to supply the CSA or use `/speckit.specify`.

### 6.7 No-Epic fallback — `/speckit.specify`

If you have a CSA diagram but no Epic, run `/speckit.specify`. The preset's `csa-extractor` parses the diagram directly: it scans `*.drawio.xml`, extracts components (nodes), integrations (edges), cloud boundaries (group containers), and protocol hints (edge labels), assigns INT-001/002/… IDs, pre-fills the integration blocks, and elicits the fields the diagram cannot reveal (auth, SLAs, criticality, target intent) — leaving `TODO:` markers rather than guessing. The deliverable is the same `spec.md` shape, so `/speckit.plan.draft` follows identically. If `/speckit.specify` finds no diagram, it directs you back to the CSA Agent workflow.

---

## 7. Spec Template (full)

→ *Architecture §4 (principle P1) explains why integration-level decomposition is the unit of work.*

```markdown
# Application Modernization Spec

## Application Summary
- **Name:**
- **Current host:** (vSphere / EC2 / mainframe / etc.)
- **Source code repo:** (URL or path)
- **Business criticality:** (Tier 1 / 2 / 3)
- **Data classification:** (Public / Internal / Confidential / Restricted)
- **Compliance regimes:** (SOX / PCI / HIPAA / GDPR / none)

## Modernization Scope
- **Integrations in scope this iteration:** (comma-separated integration IDs)
- **Integrations explicitly out of scope:** (with reason)
- **Target AWS account:** (account ID, region)
- **Cross-cloud dependencies:** (any GCP/Azure systems the target will consume)

## Integration Inventory

### Integration: INT-XXX — <short name>

**Functional category** (multi-label, pick all that apply):
- [ ] app_to_app_internal
- [ ] app_to_app_external
- [ ] app_to_app_cross_cloud
- [ ] spa_external_facing
- [ ] spa_internal_facing
- [ ] data_pipeline
- [ ] sso_sp / sso_idp
- [ ] file_transfer_internal / file_transfer_external
- [ ] event_driven_async
- [ ] sync_request_response

**Diagram source:** (auto-populated by csa-extractor)
- Extracted from: (diagram filename)
- Edge label: (raw label text, if any)

**Current State**
- Protocol:
- Transport:
- Auth:
- Payload schema:
- Source tech stack:
- SLA / throughput:
- Data residency:
- Criticality:
- Failure mode today:

**Target Intent**
- Preserve invariants:
- Acceptable downtime during cutover:
- Acceptable performance regression:
- Hard rejections:

**Dependencies on other integrations:**

**Cross-cloud topology (if applicable):**
- Source / target cloud:
- Latency budget across boundary:
- Required transit:

---
(Repeat per integration)

## Non-Functional Requirements (Application-Wide)
- Authentication for end users:
- Authorization model:
- Observability requirements:
- DR strategy:
- RTO / RPO:
```

---

## 8. Worked Example: `spec.md`

→ *Architecture §8 shows the CSA and TSA diagrams for this reference case.*

⚠️ **Decisions in this example you should NOT copy without evaluating for your context:**
- SAML SSO via Ping Federate — your IDP may differ
- Oracle 19c retained on-prem — your DB strategy may differ
- 48h dual-publish window — depends on YOUR downstream's idempotency contract
- Pilot Light DR — Tier 1 apps may need Warm Standby

```markdown
# Application Modernization Spec

## Application Summary
- **Name:** ClaimsPortal-MPA
- **Current host:** vSphere on-prem (DC-East cluster, 4 VMs behind F5 LTM)
- **Source code repo:** github.company.com/claims/claims-portal-mpa
- **Business criticality:** Tier 2
- **Data classification:** Confidential (PII)
- **Compliance regimes:** SOX, internal data-protection standard

## Modernization Scope
- **Integrations in scope this iteration:** INT-001, INT-002, INT-003, INT-004
- **Integrations explicitly out of scope:** none — full app refactor
- **Target AWS account:** 411222333444 (claims-prod), us-east-1
- **Cross-cloud dependencies:** Apigee on GCP `enterprise-apigee-prod`

## Integration Inventory

### Integration: INT-001 — UI rendering

**Functional category:** [x] spa_internal_facing

**Diagram source:** Extracted from claims-portal-csa.drawio.xml, edge: "User → MPA"

**Current State**
- Protocol: HTTPS
- Transport: server-rendered HTML (JSP)
- Auth: SAML SSO via on-prem Ping Federate (session cookie)
- Payload schema: HTML pages
- Source tech stack: Tomcat 9 + Spring MVC 5 + JSP
- SLA / throughput: p95 < 2s, 30 RPS peak
- Data residency: US only
- Criticality: Tier 2
- Failure mode today: blank page, full outage

**Target Intent**
- Preserve invariants: same URL paths, same SSO experience
- Acceptable downtime: 15 min (after-hours)
- Acceptable regression: p95 ≤ 2.5s first week
- Hard rejections: no CSR for /print/* pages

**Dependencies:** INT-002

### Integration: INT-002 — Server-side application logic

**Functional category:** [x] app_to_app_internal

**Diagram source:** Extracted from claims-portal-csa.drawio.xml, edge: "MPA → F5"

**Current State**
- Protocol: HTTPS REST
- Auth: SAML session, internal AD
- Payload schema: JSON, see `/docs/openapi-v3.yaml`
- Source tech stack: Spring MVC 5, Spring Data JPA, Oracle 19c
- SLA / throughput: p95 < 500ms, 30 RPS peak
- Criticality: Tier 2
- Failure mode today: 5xx to UI

**Target Intent**
- Preserve invariants: same REST contract `/api/v1/*`, Oracle retained on-prem (out of scope)
- Acceptable downtime: 15 min (paired with INT-001)
- Acceptable regression: +50ms p95
- Hard rejections: no Lambda (sustained traffic)

**Dependencies:** none — anchors cutover

### Integration: INT-003 — Domain API consumption

**Functional category:** [x] app_to_app_external, [x] app_to_app_cross_cloud, [x] sync_request_response

**Diagram source:** Extracted from claims-portal-csa.drawio.xml, edge: "MPA → APIC (REST/HTTPS)"

**Current State**
- Protocol: HTTPS REST
- Auth: OAuth2 client_credentials via APIC, mTLS to APIC edge
- Payload schema: `/docs/domain-api-v2.openapi.yaml`
- Source tech stack: Spring RestTemplate, APIC SDK 5.x
- SLA / throughput: p95 < 1s, 12 RPS peak
- Criticality: Tier 2
- Failure mode today: circuit breaker → cached read-only view

**Target Intent**
- Preserve invariants: same OpenAPI v2, same OAuth flow, same circuit-breaker semantics
- Acceptable downtime: 0 min (parallel gateway swap)
- Acceptable regression: +100ms p95 for cross-cloud hop
- Hard rejections: no AWS API Gateway (enterprise standard is Apigee)

**Dependencies:** independent of INT-001/002 after Apigee provisioned

**Cross-cloud topology:**
- Source: on-prem APIC, DC-East
- Target: GCP Apigee `enterprise-apigee-prod`
- Latency budget: 100ms p95 added
- Transit: AWS PrivateLink → GCP PSC → Apigee (per SEC-019)

### Integration: INT-004 — Async messaging

**Functional category:** [x] app_to_app_internal, [x] event_driven_async

**Diagram source:** Extracted from claims-portal-csa.drawio.xml, edge: "MPA → IBM MQ (JMS)"

**Current State**
- Protocol: JMS
- Transport: IBM MQ (CLAIMS.OUT.NOTIFY)
- Auth: TLS + MQ channel cert
- Payload schema: `/docs/notify-event-v1.json`
- Source tech stack: Spring JMS + IBM MQ client 9.1
- SLA / throughput: 500 msg/min sustained, 5000/min peak
- Criticality: Tier 2
- Failure mode today: exponential backoff; spill to file + replay after 5 min

**Target Intent**
- Preserve invariants: at-least-once, existing message contract unchanged
- Acceptable downtime: 0 min (dual-publish covers)
- Acceptable regression: none
- Hard rejections: no SNS (downstream wants point-to-point)

**Dependencies:** after INT-002 (BFF must exist to publish)

## Non-Functional Requirements
- Auth: SAML SSO via Ping Federate (Cognito deferred)
- Authz: RBAC from AD groups in SAML assertion
- Observability: Splunk logs, Dynatrace APM, OTel traces; SLO p95 < 2.5s
- DR: Pilot Light (us-east-1 → us-west-2)
- RTO / RPO: 4h / 1h
```

---

## 9. `/speckit.plan.draft` + `/speckit.plan.review`

→ *Architecture §6, stage ② explains the rationale for two-stage planning.*

### 9.1 Why two stages

R-factor decisions are contested between dev, EA, and finance. A solo 30-minute pass produces decisions that get overturned at PR review. The two-stage process separates first-pass thinking from structured review, and the acceptance telemetry shows that reviewed plans produce 20%+ better outcomes than solo-drafted plans.

### 9.2 Stage 1: `/speckit.plan.draft`

```
/speckit.plan.draft
```

The agent loads the plan template and walks you through, integration by integration. You provide your best-judgment decisions. The deliverable is `plan.md` in `draft` state.

### 9.3 Stage 2: `/speckit.plan.review`

```
/speckit.plan.review
```

The agent publishes the draft plan for async review. Mechanically, this creates a GitHub issue (or a comment on the existing modernization ticket) with the full plan and a structured review template. The designated reviewer (EA architect or LOB lead) leaves comments in a structured format:

```markdown
### Review: INT-003
- R-factor: ✓ Agree with Replatform
- Cutover: ⚠ Blue-green at gateway level is correct, but 7-day lag is aggressive.
  Consider 14-day soak given Apigee team's non-prod capacity constraints.
- Sequencing: ✓ OK

### Review: INT-004
- R-factor: ✓ Agree with Refactor
- Cutover: ✓ Dual-publish is correct
- Coexistence: ⚠ Verify downstream dedup covers the full 48h window, not just 24h
```

The developer resolves comments, updates `plan.md`, and the agent marks the plan as `reviewed`. The design contract records whether the plan was reviewed or solo-drafted.

---

## 10. Plan Template (full)

→ *Architecture §9.3 explains how plan fields drive the context-filtered substitution stage.*

```markdown
# Modernization Plan

## Global Decisions
- **Target AWS account ID:**
- **Target region (primary):**
- **Target region (DR):**
- **Landing zone version:**
- **Deployment window approval:**

## Per-Integration Decisions

### Integration: INT-XXX — <short name>

**R-Factor** (pick one):
- [ ] Rehost / Replatform / Refactor / Rewrite / Repurchase / Retire / Retain

**R-Factor justification:** (1-2 sentences)

**Target landing zone:**
- Account:
- VPC:
- Subnet tier:

**Cutover strategy** (pick one):
- [ ] Big-bang / Blue-green / Canary / Strangler-fig / Dual-publish

**Cutover strategy details:**
- Duration / window:
- Rollback trigger:
- Rollback procedure:

**Sequencing dependencies:**
- Must cut over after / before / simultaneously with:

**Coexistence constraints:**

**Data migration approach:**

**Validation gates:**
- Parity test:
- Performance test:
- Acceptance criteria: (GIVEN/WHEN/THEN)

---
(Repeat per integration)

## Cross-Cutting Decisions
- Identity / service auth / secrets / observability / CI-CD path

## Review Status
- [ ] Solo-drafted (proceed with awareness of higher revision rate)
- [ ] Reviewed by: (name, date, ticket reference)
```

---

## 11. Worked Example: `plan.md`

⚠️ **This is a worked example. Copy the structure, not the decisions.** Your r-factors, cutover windows, and sequencing depend on your app, your team, and your enterprise context.

```markdown
# Modernization Plan — ClaimsPortal-MPA

## Global Decisions
- **Target AWS account ID:** 411222333444
- **Target region (primary):** us-east-1
- **Target region (DR):** us-west-2
- **Landing zone version:** LZ-2025.3
- **Deployment window approval:** CHG-0098271 (Sat 2026-06-13, 02:00–06:00 ET)

## Per-Integration Decisions

### INT-001 — UI rendering
- **R-Factor:** Refactor (JSP → SPA, different rendering model)
- **Landing zone:** 411222333444 / claims-prod-vpc / edge + private
- **Cutover:** Big-bang (Route 53 weighted swap, paired with INT-002)
- **Rollback:** P1 in 30 min or p95 > 5s → weight back to on-prem MPA
- **Sequencing:** after INT-002, simultaneously with INT-002
- **Validation:** Selenium suite 100%; synthetic p95 < 2.5s

### INT-002 — Server-side logic
- **R-Factor:** Refactor (Spring MVC → Spring Boot BFF)
- **Landing zone:** 411222333444 / claims-prod-vpc / private (Fargate)
- **Cutover:** Strangler-fig (feature flag on CloudFront `/api/v1/*`)
- **Rollback:** 5xx > 2% or p95 > 1s → flip flag off
- **Sequencing:** anchors; before INT-001
- **Coexistence:** BFF → on-prem Oracle (DB retained, +25ms hop)
- **Validation:** API replay 5000 requests, p95 < 600ms

### INT-003 — Domain API (cross-cloud)
- **R-Factor:** Replatform (APIC SDK → Apigee SDK, contract preserved)
- **Landing zone:** 411222333444 / claims-prod-vpc / private; PrivateLink → GCP PSC
- **Cutover:** Blue-green at gateway; lags INT-001/002 by 14 days (soak)
- **Rollback:** 4xx/5xx > 1% or circuit breaker → flip config to APIC
- **Sequencing:** after INT-001, INT-002; APIC kept live 30 days
- **Validation:** parity validator (shadow 14 days, diff < 0.1%); latency ≤ +100ms

### INT-004 — Async messaging
- **R-Factor:** Refactor (MQ JMS → AWS SDK SQS)
- **Landing zone:** 411222333444 / claims-prod-vpc / private; SQS VPC endpoint
- **Cutover:** Dual-publish for 48h
- **Rollback:** duplicate-rate > 1% or missing messages → revert to MQ-only
- **Sequencing:** after INT-002
- **Coexistence:** downstream deduplicates by event_id (ticket DSN-4471)
- **Validation:** 24h load test; SQS publish p95 < 50ms

## Cross-Cutting Decisions
- Identity: SAML SSO via Ping Federate (Cognito deferred)
- Service auth: mTLS to Apigee (cert in Secrets Manager); IAM for SQS
- Secrets: AWS Secrets Manager
- Observability: Splunk `splunk-hec.internal:8088`; Dynatrace OneAgent; OTel sidecar
- CI/CD: GitHub Action → Harness `claims-portal-bff`

## Review Status
- [x] Reviewed by: J. Martinez (EA Architect), 2026-06-01, JIRA EA-4522
```

---

## 12. `/accelerator.blueprint`

→ *Architecture §9 covers the async MCP Tasks design and the 4-stage internal pipeline.*

> **First-time authentication:** The first time you run `/accelerator.blueprint` or `/accelerator.assess`, your coding agent opens a browser for company SSO login (Microsoft Entra ID, OAuth 2.1). After authenticating once (including MFA), tokens are cached securely in your OS keychain. Subsequent commands use silent token refresh — no browser popup. Both the Solution Accelerator and Governance Guardian share the same authentication. See Architecture Document §17.2 for the full OAuth 2.1 flow.

```
/accelerator.blueprint
```

The Solution Accelerator uses the **MCP Tasks async protocol** because VS Code Copilot enforces a hard 10–15 second timeout on MCP tool calls, and the internal pipeline can take 1–30 minutes depending on integration count. Instead of one blocking call, three fast MCP tools work together:

**What you see in the Chat pane:**

```
You: /accelerator.blueprint

Agent: Blueprint generation started (task abc-123). Checking progress...
Agent: Stage ④: substitution — 4 integrations resolved ✓
Agent: Stage ⑤: pattern retrieval for INT-001...
Agent: Stage ⑤: pattern retrieval for INT-003 (cross-cloud)...
Agent: Stage ⑤: composition validation ✓ (14 rules checked)
Agent: Stage ⑥: ADR compliance — 4 integrations passed ✓
Agent: Stage ⑦: assembling blueprint + contract + diagrams...
Agent: Blueprint ready. Writing app-blueprint.md and design_contract.json
       to your workspace. Review the 4 Draw.io diagrams inline.
```

**What happens under the hood:**

1. The prompt file calls `blueprint_start` with your spec + plan as JSON. The MCP server validates the input, creates a background task, and returns a `taskId` — all within 2 seconds.
2. The prompt file polls `blueprint_status(taskId)` every 10 seconds. Each poll returns the current pipeline stage and a progress message. The agent reports these to you in the Chat pane.
3. The background job (Cloud Run Jobs, no timeout constraint) runs the 4-stage pipeline: ④ context-filtered substitution → ⑤ semantic pattern retrieval + LLM composition → ⑥ ADR compliance check → ⑦ blueprint + contract + diagram assembly.
4. When the poll returns `status: "completed"`, the prompt file calls `blueprint_result(taskId)` to retrieve the output and writes all files to your workspace:
   - **`app-blueprint.md`** — PRIMARY artifact. Human-readable structured markdown (12 sections (Part I: §1-§7 governance + Part II: §8-§12 technical)). You edit THIS file.
   - **`app-blueprint.json`** — DERIVED artifact. Machine-readable JSON generated from `.md` by `assemble_blueprint`. Consumed by `/accelerator.generate`. **Never edit this file directly** — it's regenerated from `.md` automatically.
   - **`design_contract.json`** — Design contract with provenance, attestations, migration phases.
   - **Diagram files** — `.drawio.xml` (editable in Draw.io VSCode extension) + `.png` (auto-rendered, inline in markdown).

If anything fails — substitution unresolved, ADR rejected, composition invalid — the poll returns `status: "failed"` with a structured error. You get the same actionable error messages as before; they just arrive via the polling mechanism.

**Timing:** For the reference case (4 integrations), expect 2–5 minutes. For a complex app with 15 integrations, expect 15–30 minutes. You can continue working in other files during the poll — the agent will notify you when the blueprint is ready.

**If the task takes too long (>30 minutes):** See §18 FM-9.

---

## 13. Reviewing the Blueprint and Design Contract

→ *Architecture §9.6 provides the full design contract schema.*

**Editing diagrams — choose your tool:** Your workspace contains 4 formats per diagram. Edit whichever you prefer — the others are re-rendered when `assemble_blueprint` runs (auto-called by `/accelerator.generate` if `.md` changed):

| Tool | VSCode Extension | File to open |
|---|---|---|
| **Draw.io** | `hediet.vscode-drawio` extension | `*.drawio.xml` — live visual editor |
| **Draw.io** | `hediet.vscode-drawio` extension | `*.drawio.xml` — full draw.io editor |

Check in this order:

1. **Lifecycle state.** Should be `LIVE`.
2. **Confidence per integration.** `< 0.85` → read `alternatives:`.
3. **`requires_review` flags.** Any present → do not run `/accelerator.generate`. Fix spec or pick alternative.
4. **Phase-0 entries.** Cross-cloud plumbing steps? Coordinate with external teams now.
5. **ADR attestations.** Match EA expectations? Surprises → investigate.
6. **Tech substitutions.** `source_tokens` → `target_tokens` correct?
7. **Migration phases.** Ordering and durations correct?
8. **IaC module versions.** Current?

---

## 13a. `/accelerator.assess` — Governance assessment

→ *Governance Guardian Architecture Extension covers the full assessment flow, solution package schema, scorecard format, and MCP tool definitions.*

After reviewing the blueprint and design contract, run the governance assessment before generating code:

```
/accelerator.assess
```

The coding agent reads `app-blueprint.md` (NOT `app-blueprint.json` — governance assesses the human-readable architecture, not the machine-readable JSON) and extracts the 7 governance sections from Part I (§1-§7): §1 Executive Summary, §2 Tech Stack, §3 Architecture Decision Log, §4 NFRs, §5 Patterns & Agent Topology, §6 Component Architecture (PNG), §7 HA/DR Views (PNGs) — packages them as an ephemeral solution_package (transport JSON, not the `.json` file), and sends to the Governance Guardian MCP Server via async MCP Tasks (same pattern as Solution Accelerator). The `app-blueprint.json` file is untouched during governance.

You see progress in the Chat pane: "Evaluating architecture compliance...", "Checking pattern adherence...", "Scoring HA/DR readiness...". When complete, you receive a scorecard (7 categories, 0–100 each) and findings (showstopper / high / medium / low).

**If showstoppers:** Fix them (e.g., add cross-region DR per ADR-205), then re-run `/accelerator.assess`. Repeat until no showstoppers.

**If no showstoppers:** Proceed to `/accelerator.generate`. Remaining findings will be recorded as tech debt.

---

## 14. `/accelerator.generate`

→ *Architecture doc Part II §11 documents brownfield-specific CI/CD and migration phase configurations.*

```
/accelerator.generate
```

**Governance gate (Step 0):** Before generation runs, the coding agent calls `recordTechDebt` on the Governance Guardian MCP Server. If showstoppers remain → BLOCKED. If no showstoppers → remaining findings recorded as tech debt, generation proceeds. If no assessment exists → warning with skip option.

**Brownfield-aware generation (Steps 1–18)** produces:

- **Application code** — BFF with feature-flag scaffolding for strangler-fig, dual-publish config for MQ→SQS, Apigee client with circuit breaker
- **IaC** — Terraform generated via `company-terraform` skill: reads company module repos via **GitHub MCP Server** (`variables.tf`, `outputs.tf`), maps blueprint fields to module variables deterministically, generates compliant Terraform referencing company modules (never raw `aws_*` resources). Pattern repos provide the scaffold; service modules provide building blocks.
- **CI/CD** — Harness pipeline with `/accelerator.refresh` gate before deploy
- **Runtime compliance** — AWS Config rules generated from `adr_attestations[]`
- **Transition artifacts** — feature-flag configs, dual-publish toggle, Phase-0 checklist

→ *Architecture §12 covers runtime compliance verification.*

---

## 15. `/accelerator.refresh` — Keeping Contracts Alive

→ *Architecture §11 covers the full lifecycle design.*

### 15.1 When you need it

Your design contract goes **STALE** when any peripheral store changes after generation (new ADR ratified, substitution table updated, IaC module version bumped). The pre-commit hook detects this and warns you. After 30 days stale, the contract becomes **EXPIRED** and all actions are blocked.

### 15.2 Run it

```
/accelerator.refresh
```

The agent re-runs the Solution Accelerator against your existing spec/plan and shows a diff:

```
Agent: Contract refresh complete. Changes detected:

       ADR-722 (model armor) — attestation updated (rule revised 2026-06-15)
       tf-modules/sqs-producer — v3.2.0 → v3.3.0 (non-breaking, security patch)
       No pattern changes. No substitution changes.

       Accept these changes? [Y/n]
```

Accept returns the contract to `LIVE`. Reject keeps it `STALE` (you can investigate further).

### 15.3 Long-lived projects

If your project takes 6+ months:
- `/accelerator.refresh` is required before every PR (pre-commit hook enforces)
- `/accelerator.refresh` is required before every deploy (Harness pipeline gate enforces)
- If the contract has been refreshed >3 times, the quarterly governance review will flag it for possible re-scoping

---

## 16. Custom Agent & Prompt Files

→ *Architecture §2 covers the Spec Kit command-namespace mapping.*

The preset ships six prompt files (`.github/prompts/`) and two custom agents (`.github/agents/`). Each prompt file's YAML frontmatter pins a model with fallback, declares tools, and carries the system prompt. You can customize any file in your project repo without forking the preset.

Common customizations:
- Pin to a specific model only
- Add company-specific elicitation questions to the agent
- Add team-specific shorthand to the instructions file

Defaults are restored with `specify preset reset`.

---

## 17. Quality Self-Checks

### Spec checklist (10 items)

| # | Question |
|---|---|
| 1 | Every integration block has all four sub-sections? |
| 2 | Every integration has ≥1 functional category? |
| 3 | Every integration has a current-state SLA? |
| 4 | Cross-cloud integrations specify transit method? |
| 5 | Hard rejections documented per integration? |
| 6 | Diagram source section populated? |
| 7 | Payload schemas linked (not just described)? |
| 8 | Failure modes captured per integration? |
| 9 | Dependencies expressed as INT-IDs? |
| 10 | Application-wide DR strategy specified? |

### Plan checklist (10 items)

| # | Question |
|---|---|
| 1 | Every INT-XXX from spec has a plan block? |
| 2 | Every r-factor has justification? |
| 3 | Sequencing dependencies form valid DAG? |
| 4 | Every dual-operation window has downstream mitigation? |
| 5 | Every cutover has rollback procedure? |
| 6 | Acceptance criteria in GIVEN/WHEN/THEN? |
| 7 | Deployment window approval present? |
| 8 | Cross-cutting decisions confirmed? |
| 9 | Review status filled (solo or reviewed)? |
| 10 | Cross-cloud integrations have Phase-0 lead-time considered in sequencing? |

---

## 18. Common Failure Modes & Fixes

### FM-0: Slash commands don't appear

**Diagnosis:** Not in Agent mode; workspace not repo root; extension outdated; Spec Kit prompt-file discovery issue.
**Fix:** Agent mode + repo root + latest extensions. If still broken: `specify init --here --force`.

### FM-1: No diagram found in workspace

**Diagnosis:** No `.drawio.xml` files in the workspace.
**Fix:** The CSA Agent (upstream, separate system) must produce the diagram first. Return to the CSA Agent workflow, then re-run `/speckit.specify` once the diagram is in the workspace. → *Architecture §7 covers the handoff boundary.*

### FM-2: Tech substitution unresolved

**Diagnosis:** Table doesn't have your `(source_tech, r_factor, context)`.
**Fix:** File `SDLC-ACCELERATORS-SUBSTITUTIONS` ticket. → *Operating Playbook §5, §11.*

### FM-3: ADR rejection

**Diagnosis:** Plan violates enterprise policy.
**Fix:** Change plan or request EA waiver. → *Operating Playbook §4.5.*

### FM-4: Low confidence on pattern selection

**Diagnosis:** Spec too ambiguous.
**Fix:** Rewrite integration intent paragraph with specific signal words. → *Architecture §9.3.*

### FM-5: Composition validation fails

**Diagnosis:** Incompatible patterns composed.
**Fix:** Split integration or change cutover strategy in plan. → *Architecture §9.2.*

### FM-6: Cross-cloud plumbing incomplete

**Diagnosis:** Phase-0 exit criteria not met.
**Fix:** Check `design_contract.json` → `migration_phases[phase:0]` → `checklist_ref`. Coordinate with GCP networking and Apigee teams. The IaC for your side is generated; the GCP side requires external provisioning. → *Architecture §15.*

### FM-7: Design contract stale/expired

**Diagnosis:** Pre-commit hook blocks or warns.
**Fix:** Run `/accelerator.refresh`, review diff, accept changes. → *§15.*

### FM-8: Constitution contradiction

**Diagnosis:** Pre-commit hook blocks with specific enterprise rule ID.
**Fix:** Remove or reword the conflicting project rule in `constitution-project.md`. → *§5.*

### FM-9: Blueprint task running too long (>30 minutes)

**Diagnosis:** `blueprint_status` keeps returning `working` for more than 30 minutes. The most common cause is a large integration count (>10) combined with slow Vertex AI Search responses or a complex composition-validation pass.
**Fix:** Cancel the task and simplify. Common strategies: split the spec into two batches (first batch: the 5 highest-priority integrations; second batch: the rest), or reduce ambiguity in integration intent paragraphs so pattern retrieval resolves faster. If the problem persists, file an `SDLC-ACCELERATORS-ADVISOR` ticket — platform engineering will investigate which pipeline stage is the bottleneck. → *Architecture §9.3.2 covers task lifecycle.*

---

## 19. FAQ

**Q: Can I skip the diagram extraction and write spec.md manually?**
A: Yes. Write your own `spec.md` conforming to the template and proceed to `/speckit.plan.draft`. You lose the diagram-based pre-fill but are not blocked.

**Q: What if my plan review takes too long?**
A: The review is async — work on other things while waiting. If your reviewer is unresponsive, escalate in `#sdlc-accelerators`. Solo-drafted plans are permitted but the design contract records the review status, and acceptance telemetry shows solo plans have ~20% higher revision rates at PR.

**Q: Can I edit the blueprint and skip `/accelerator.blueprint`?**
A: Yes. The coding agent only needs `app-blueprint.md` and `design_contract.json`. You lose AI-guided recommendation and ADR attestation.

**Q: How do I handle a multi-app modernization?**
A: One `spec.md` and `plan.md` per target service. Each gets its own blueprint and generate invocation.

**Q: What about Visio files?**
A: Convert to drawio first (draw.io: File → Import). Native Visio support is on the roadmap.

**Q: What happens when Claude Opus 4.6 disappears?**
A: The prompt file's model array falls back automatically to Opus 4.7 then Sonnet 4.6. Quality degrades ~5%. → *Operating Playbook §9.*

**Q: How often should I run `/accelerator.refresh`?**
A: At minimum before every PR. For long-lived projects, run weekly as a hygiene check.

---

### System Prompt Template — Brownfield Solution Accelerator

→ *Referenced from Architecture Document §9.2 (Solution Accelerator internal components — company system prompt).*

The **Solution Accelerator Agent** — the single ADK agent the MCP server delegates to — carries **two FunctionTools**, each bound to a curated system prompt maintained by platform engineering (updated quarterly with the EA office): `recommend_architecture` uses the CSA→TSA transformation prompt below; `create_epic_signal_ledger` uses the extractive epic-shaping prompt (Architecture § "Epic-to-Spec Fusion"). The transformation prompt guides the agent's reasoning about CSA→TSA.

```markdown
You are the Solution Accelerator for brownfield CSA→TSA transformations. You receive a structured spec (with current-state integrations extracted from a CSA diagram) and a technical plan (with r_factor, cutover strategy, and migration sequencing).

Your job is to produce an opinionated Target State Architecture (TSA) blueprint by:

1. **Map current to target:** For each integration in spec §4, look up the tech substitution decision table. Apply the company-approved target technology. Flag low-confidence substitutions (< 0.85) with `requires_review: true`.

2. **Compose patterns:** Read the workflow ordering words in spec §2. Select agentic patterns from the pattern catalog (Sequential, Parallel, Loop, HITL). For brownfield, ALWAYS consider Strangler-Fig when cutover_strategy is "strangler-fig". Validate composition rules (LoopAgent cannot nest inside ParallelAgent).

3. **Discover tools and agents:** Search the tool registry (Vertex AI Search) for MCP servers matching each integration. Search Apigee API Hub for deployed A2A agents (`type=a2a_agent`). Priority: A2A (reuse) > MCP (tool) > Build (new).

4. **Enforce ADR compliance:** Check every selection against the ADR constraint store. If a selection violates an ADR (e.g., "Oracle is prohibited — use Aurora PostgreSQL"), substitute and note the attestation.

5. **Generate migration phases:** From plan.md sequencing, generate `migration_phases[]` with scope, coexistence mode, and rollback procedure per phase. Always start with read-path migration (lowest risk).

6. **Assemble blueprint:** Generate `app-blueprint.md` (PRIMARY) + `app-blueprint.json` (DERIVED) + diagrams rendered by the Eraser MCP server (DSL → `.drawio.xml` + `.png`).

CONSTRAINTS:
- NEVER recommend technologies not in the company's approved tech radar.
- ALWAYS generate migration phases — brownfield blueprints without phases are incomplete.
- ALWAYS flag cross-cloud egress patterns (PrivateLink + PSC) when source and target are on different clouds.
- Tag every recommendation with a confidence score (0.0–1.0).
```

---

*End of developer guide.*

---

## Appendix — MPA→SPA Use Case: Complete Brownfield Sample Files

This appendix contains every MPA→SPA-specific sample for the brownfield CSA→TSA SpecKit preset. Template files (empty structures) are in the Brownfield Architecture Document Appendix.

**Reference case:** Insurance company migrating from vSphere-hosted Tomcat + JSP MPA with Oracle DB to Angular SPA + Spring Boot BFF on AWS ECS Fargate with Aurora PostgreSQL. 15 integrations, 3 migration phases, Strangler-Fig cutover.

---

### MPA-T1 — Filled spec.md

```markdown
---
template: sdlc-accelerators-brownfield-spec
version: "2.0"
archetype: brownfield-migration
use_case: insurance-mpa-to-spa
---

# Application Specification — Insurance Portal MPA→SPA

## 1. Business Context
Our auto insurance customer portal handles policy lookup, claims submission, billing, and document management. It serves 50,000 daily active users. The current MPA is a Tomcat 8.5 + JSP application on vSphere 7.x with an Oracle 19c database. Page load times average 4.2 seconds, mobile experience is poor (no responsive design), and deploying changes requires a full application restart with 15-minute downtime windows. We want to modernize to a responsive SPA with a BFF backend on AWS, reducing page loads to < 1 second and enabling zero-downtime deployments.

## 2. Current State — What Exists Today
- **Frontend:** JSP pages (312 JSP files) served by Tomcat 8.5 on vSphere VMs (4 VMs, load-balanced by F5)
- **Backend:** Java servlets (monolithic WAR) with JDBC connections to Oracle
- **Database:** Oracle 19c on dedicated vSphere VM (16 cores, 64GB RAM)
- **Messaging:** IBM MQ for async claim processing (3 queues)
- **Batch:** Nightly SFTP file transfers to reporting data warehouse
- **Authentication:** On-prem LDAP (Active Directory)
- **Infrastructure:** vSphere 7.x, 12 VMs total, US-East datacenter

## 3. Target Intent — What We Want
Modernize to a responsive SPA frontend with a Spring Boot BFF backend deployed on AWS. Decompose the monolith into domain-aligned services (policy, claims, billing, documents). Enable zero-downtime deployments and auto-scaling. Use Strangler-Fig pattern for phased migration over 6 months.

## 4. Integrations — Current State (pre-filled from CSA diagram)
CURRENT: OracleDB-PolicyStore | TYPE: sync | PROTOCOL: JDBC | OWNER: policy-team
CURRENT: OracleDB-ClaimsStore | TYPE: sync | PROTOCOL: JDBC | OWNER: claims-team
CURRENT: OracleDB-BillingStore | TYPE: sync | PROTOCOL: JDBC | OWNER: billing-team
CURRENT: IBM-MQ-ClaimQueue | TYPE: async | PROTOCOL: MQ | OWNER: claims-team
CURRENT: IBM-MQ-NotifyQueue | TYPE: async | PROTOCOL: MQ | OWNER: notification-team
CURRENT: IBM-MQ-AuditQueue | TYPE: async | PROTOCOL: MQ | OWNER: compliance-team
CURRENT: SFTP-ReportingDW | TYPE: batch | PROTOCOL: SFTP/CSV | OWNER: analytics-team
CURRENT: LDAP-AuthN | TYPE: sync | PROTOCOL: LDAP | OWNER: identity-team
CURRENT: F5-LoadBalancer | TYPE: sync | PROTOCOL: HTTP | OWNER: infra-team
CURRENT: SMTP-EmailGateway | TYPE: async | PROTOCOL: SMTP | OWNER: notification-team
CURRENT: PrintService | TYPE: sync | PROTOCOL: REST | OWNER: document-team
CURRENT: GeocodingAPI | TYPE: sync | PROTOCOL: REST | OWNER: external (Google)
CURRENT: CreditCheckAPI | TYPE: sync | PROTOCOL: SOAP | OWNER: external (Experian)
CURRENT: PaymentGateway | TYPE: sync | PROTOCOL: REST | OWNER: external (Stripe)
CURRENT: DocumentStore | TYPE: sync | PROTOCOL: NFS | OWNER: document-team

## 5. External Partners & Integrations
- Body shop network — they operate their own system (A2A)
- Experian credit check — external SOAP API
- Stripe payment gateway — external REST API
- Google geocoding — public REST API

## 6. What We Own vs What We Connect To
- We OWN: Portal frontend, BFF backend, all databases, MQ queues, batch jobs, document store
- We CONNECT TO: LDAP (shared identity infra), F5 (shared infra), Experian (external), Stripe (external), Google (external), Body shop (partner)

## 7. Business Rules
IF policy_type = "comprehensive" AND claim_amount > deductible THEN auto_approve = true
IF policy_type = "third_party_only" AND claim_type = "own_damage" THEN reject WITH reason = "not_covered"
IF payment_amount > 10000 THEN require_dual_approval = true
IF document_type = "claim_photo" THEN max_size = 10MB AND format IN ["jpg", "png"]

## 8. Transformation Rules
MIGRATE OracleDB-PolicyStore TO Aurora-PolicyDB USING trickle-migration (dual-write during coexistence)
MIGRATE OracleDB-ClaimsStore TO Aurora-ClaimsDB USING trickle-migration
MIGRATE OracleDB-BillingStore TO Aurora-BillingDB USING trickle-migration
MIGRATE IBM-MQ-ClaimQueue TO Amazon-SQS-ClaimQueue USING message-format-mapping
MIGRATE SFTP-ReportingDW TO S3+EventBridge USING trigger-based-processing
MIGRATE LDAP-AuthN TO Cognito+EntraID USING identity-federation
MIGRATE NFS-DocumentStore TO S3-DocumentBucket USING bulk-copy + CDN

## 9. Error Handling
IF Oracle and Aurora dual-write conflict: Aurora wins (primary), log Oracle delta for reconciliation
IF MQ message stuck in dead-letter: auto-retry 3x, then alert claims-team Slack channel
IF Strangler-Fig proxy cannot reach new system: fallback to old system, log, alert
IF phase rollback triggered: stop dual-write, revert proxy, verify data consistency

## 10. Acceptance Criteria
GIVEN the old JSP portal serving requests WHEN Phase 1 routes read-path to new SPA THEN zero user-facing errors and < 2 second page load
GIVEN dual-write enabled WHEN claim created in new system THEN claim also appears in old Oracle DB within 5 seconds
GIVEN Phase 2 complete WHEN all write-path on new system THEN Oracle is read-only backup
GIVEN Phase 3 complete WHEN old system decommissioned THEN all 50,000 DAU served by new SPA with 99.9% uptime
GIVEN Strangler-Fig proxy WHEN new system fails THEN automatic fallback to old system within 30 seconds
```

---

### MPA-T2 — Filled plan.md

```markdown
---
template: sdlc-accelerators-brownfield-plan
version: "2.0"
archetype: brownfield-migration
use_case: insurance-mpa-to-spa
---

# Technical Plan — Insurance MPA→SPA

## Infrastructure
- **Current platform:** vSphere 7.x, on-prem datacenter, US-East
- **Target cloud:** AWS us-east-1
- **Target DR region:** AWS us-west-2
- **DR strategy:** hot-standby

## Migration Strategy
- **R-factor:** Refactor (MPA→SPA + BFF decomposition)
- **Cutover strategy:** strangler-fig
- **Coexistence period:** 6 months (old Tomcat + new SPA/BFF running in parallel)
- **Data migration approach:** trickle-migration with dual-write

## Sequencing
- **Phase 1 (Month 1-2):** Read-path migration — policy lookup, vehicle lookup, document viewing. Angular SPA serves these pages. Old Tomcat handles writes.
- **Phase 2 (Month 3-4):** Write-path migration — claim submission, billing payments, document upload. Dual-write: new system primary, Oracle backup.
- **Phase 3 (Month 5-6):** Decommission — remaining batch jobs, MQ migration, LDAP→Cognito, old system shutdown.
- **Cross-cloud egress:** AWS PrivateLink for vSphere→AWS during coexistence. GCP PSC for BFF→GCP services (if any).

## Model Selection
- **Primary LLM:** gemini-2.0-flash (for BFF logic generation and agentic components)
- **Fallback LLM:** gemini-2.0-flash-lite

## CI/CD
- **Infrastructure pipeline:** Harness
- **Application pipeline:** Harness
- **IaC module source:** github.com/[company]/terraform-modules

## Observability
- **APM:** Dynatrace
- **Logging:** Splunk
- **Tracing:** Cloud Trace + Arize Phoenix
```

---

### MPA-F2 — app-blueprint.json (MPA→SPA example, abbreviated)

```json
{
  "metadata": {
    "name": "insurance-portal-spa",
    "version": "1.0.0",
    "archetype": "brownfield-migration",
    "description": "Insurance portal MPA→SPA transformation with Strangler-Fig migration",
    "team": "portal-engineering",
    "lob": "auto-insurance"
  },
  "pattern_composition": {
    "root_pattern": "Strangler-Fig",
    "composition": ["Strangler-Fig", "BFF", "SPA", "Sequential"]
  },
  "agents": [
    { "name": "portal_coordinator", "type": "SequentialAgent", "role": "Root orchestrator", "parent": null },
    { "name": "policy_bff", "type": "LlmAgent", "role": "Policy domain BFF service", "parent": "portal_coordinator", "tools": ["aurora-policy-db", "policy-cache"] },
    { "name": "claims_bff", "type": "LlmAgent", "role": "Claims domain BFF service", "parent": "portal_coordinator", "tools": ["aurora-claims-db", "sqs-claim-queue", "body-shop-a2a"] },
    { "name": "billing_bff", "type": "LlmAgent", "role": "Billing domain BFF service", "parent": "portal_coordinator", "tools": ["aurora-billing-db", "stripe-payment"] },
    { "name": "document_bff", "type": "LlmAgent", "role": "Document domain BFF service", "parent": "portal_coordinator", "tools": ["s3-document-store"] }
  ],
  "tools": {
    "mcp_servers": [
      { "name": "aurora-policy-db", "endpoint": "mcp://aurora-policy.internal:8080", "auth_method": "mtls", "assigned_to": "policy_bff", "discovered_via": "Vertex AI Search" },
      { "name": "aurora-claims-db", "endpoint": "mcp://aurora-claims.internal:8080", "auth_method": "mtls", "assigned_to": "claims_bff", "discovered_via": "Vertex AI Search" },
      { "name": "stripe-payment", "endpoint": "https://api.stripe.com/v1", "auth_method": "api_key", "assigned_to": "billing_bff", "discovered_via": "Vertex AI Search" }
    ],
    "a2a_agents": [
      { "name": "body-shop-a2a", "endpoint": "https://bodyshop.partner.com/a2a", "capabilities": ["estimate", "schedule"], "assigned_to": "claims_bff", "discovered_via": "Apigee API Hub (type=a2a_agent, v2.3, active)" }
    ]
  },
  "migration_phases": [
    { "name": "phase-1-read-path", "scope": ["policy_lookup", "vehicle_lookup", "document_viewing"], "coexistence": "dual-read", "rollback": "switch_proxy_back_to_old", "sequence_order": 1 },
    { "name": "phase-2-write-path", "scope": ["claim_submit", "billing_payment", "document_upload"], "coexistence": "dual-write", "rollback": "stop_dual_write_revert_to_old", "sequence_order": 2 },
    { "name": "phase-3-decommission", "scope": ["batch_jobs", "mq_migration", "ldap_to_cognito", "old_system_shutdown"], "coexistence": "none", "rollback": "not_applicable", "sequence_order": 3 }
  ],
  "coexistence_constraints": [
    { "system": "Oracle PolicyStore", "constraint": "read-only after Phase 2", "duration": "Phase 2-3 (months 3-6)" },
    { "system": "IBM MQ", "constraint": "message format mapping required", "duration": "Phase 3 only" },
    { "system": "LDAP", "constraint": "identity federation during transition", "duration": "Phase 3 only" }
  ],
  "csa_to_tsa_mappings": [
    { "current": "Tomcat 8.5 + JSP", "target": "Angular 17 SPA + Spring Boot 3.2 BFF on ECS Fargate", "confidence": 0.92, "migration_strategy": "refactor" },
    { "current": "Oracle 19c", "target": "Aurora PostgreSQL 15", "confidence": 0.90, "migration_strategy": "trickle-migration" },
    { "current": "IBM MQ", "target": "Amazon SQS/SNS", "confidence": 0.90, "migration_strategy": "message-format-mapping" },
    { "current": "SFTP batch", "target": "S3 + EventBridge", "confidence": 0.85, "migration_strategy": "trigger-based" },
    { "current": "on-prem LDAP", "target": "Cognito + Entra ID", "confidence": 0.80, "migration_strategy": "identity-federation" },
    { "current": "F5 LB", "target": "ALB + WAF", "confidence": 0.95, "migration_strategy": "rule-migration" }
  ],
  "blueprint_hash": "sha256:b2c3d4e5f6a7...",
  "spec_hash": "sha256:e5d4c3b2a1f6...",
  "plan_hash": "sha256:2b3c4d5e6f1a..."
}
```

---

### MPA-S1 — brownfield-migration skill output sample

```python
# coexistence/strangler_proxy.py — Generated by /accelerator.generate (brownfield-migration skill)

import httpx
import logging

logger = logging.getLogger(__name__)

PHASE_CONFIG = {
    "phase-1-read-path": {
        "migrated_types": ["policy_lookup", "vehicle_lookup", "document_viewing"],
        "coexistence": "dual-read",
    },
    "phase-2-write-path": {
        "migrated_types": ["claim_submit", "billing_payment", "document_upload"],
        "coexistence": "dual-write",
    },
}

class StranglerProxy:
    """Routes requests to old Tomcat or new SPA/BFF based on current migration phase."""

    def __init__(self, current_phase: str):
        self.old_endpoint = "https://tomcat-legacy.internal:8443"
        self.new_endpoint = "https://spa-bff.us-east-1.elb.amazonaws.com"
        self.phase = PHASE_CONFIG.get(current_phase, {})

    async def route(self, request_type: str, request_data: dict) -> dict:
        if request_type in self.phase.get("migrated_types", []):
            try:
                result = await self._call_new(request_type, request_data)
                if self.phase.get("coexistence") == "dual-write":
                    await self._call_old(request_type, request_data)  # backup write
                return result
            except Exception as e:
                logger.error(f"New system failed for {request_type}: {e}. Falling back to old.")
                return await self._call_old(request_type, request_data)
        return await self._call_old(request_type, request_data)
```

---

### MPA-S2 — spa-frontend skill output sample

```typescript
// frontend/src/app/policy/policy-lookup.component.ts — Generated (spa-frontend skill)

import { Component, OnInit } from '@angular/core';
import { PolicyService } from '../services/policy.service';
import { Policy } from '../models/policy.model';

@Component({
  selector: 'app-policy-lookup',
  template: `
    <div class="policy-container">
      <input [(ngModel)]="policyNumber" placeholder="Enter policy number" />
      <button (click)="lookupPolicy()">Search</button>
      <app-policy-card *ngIf="policy" [policy]="policy"></app-policy-card>
    </div>
  `,
})
export class PolicyLookupComponent implements OnInit {
  policyNumber = '';
  policy: Policy | null = null;

  constructor(private policyService: PolicyService) {}

  async lookupPolicy(): Promise<void> {
    this.policy = await this.policyService.getPolicy(this.policyNumber);
  }
}
```

---

### MPA-S3 — bff-backend skill output sample

```java
// backend/src/main/java/com/company/bff/service/PolicyService.java — Generated (bff-backend skill)

@Service
public class PolicyService {

    private final WebClient auroraClient;  // from blueprint tools.mcp_servers[0]

    public PolicyService(@Qualifier("aurora-policy-db") WebClient auroraClient) {
        this.auroraClient = auroraClient;
    }

    public Mono<PolicyResponse> lookupPolicy(String policyNumber) {
        return auroraClient.get()
            .uri("/policies/{id}", policyNumber)
            .retrieve()
            .bodyToMono(PolicyResponse.class)
            .timeout(Duration.ofSeconds(15))
            .retryWhen(Retry.backoff(2, Duration.ofMillis(500)));
    }
}
```

---

### MPA-P1 — speckit.specify interaction sample

```
Developer: /speckit.specify

Coding Agent: Scanning workspace for CSA diagram...
  → Found: insurance-portal-csa.drawio.xml

Coding Agent: Parsing CSA diagram...
  → Extracted 15 integration points from 23 nodes and 31 edges.
  → System types: 3 databases, 3 MQ queues, 1 batch (SFTP), 1 auth (LDAP),
    1 load balancer, 1 email, 1 print, 3 external APIs, 1 file store

Coding Agent: Creating spec.md from template...
  → §4 pre-filled with 15 integrations (all marked requires_review: true)

spec.md created with 15 integrations pre-filled from CSA diagram.
Fill in remaining sections (§1-§3, §5-§10).
```

---

### MPA-P4 — accelerator.blueprint interaction sample

```
Developer: /accelerator.blueprint

Coding Agent: Connecting to Solution Accelerator MCP Server...
Coding Agent: ✓ blueprint_start called — taskId: bp-2026-05-23-mpa
Coding Agent: Polling blueprint_status...
  → Stage: mapping — "Mapping 15 CSA integrations to target-state technologies..."
  → Stage: mapping — "Oracle 19c → Aurora PostgreSQL (confidence: 0.90)"
  → Stage: mapping — "IBM MQ → Amazon SQS (confidence: 0.90)"
  → Stage: recommending — "Composing: Strangler-Fig + BFF + SPA + Sequential..."
  → Stage: recommending — "Discovering A2A agents in API Hub..."
  → Stage: checking — "Validating ADR compliance (6 ADR attestations)..."
  → Stage: assembling — "Generating 3 migration phases (strangler-fig)..."
  → Stage: assembling — "Rendering diagrams via the Eraser MCP server..."
  → Stage: assembling — "Generating app-blueprint.json from .md..."
  → Stage: completed

Coding Agent: ✓ blueprint_result retrieved. Writing to workspace:
  → app-blueprint.md (PRIMARY — 12 sections (Part I: §1-§7 governance + Part II: §8-§12 technical), 412 lines, 15 integrations)
  → app-blueprint.json (DERIVED — machine-readable, 245 lines)
  → design_contract.json (migration_phases[], coexistence_constraints[], csa_to_tsa_mappings[])
  → portal-component-diagram.png + .drawio.xml
  → portal-hadr-diagram.png + .drawio.xml

Blueprint ready. Review app-blueprint.md — pay attention to:
  ⚠ 2 integrations flagged requires_review (LDAP: 0.80, SFTP: 0.85)
  ✓ 3 migration phases generated (read-path → write-path → decommission)
  ✓ 6 ADR attestations (Oracle prohibited, MQ deprecated, LDAP federate)
```

---

### MPA-P7 — accelerator.refresh interaction sample

```
Developer: /accelerator.refresh

Coding Agent: Reading current design contract...
  → Last generated: 2026-04-15 (38 days ago)

Coding Agent: Re-running Solution Accelerator with refresh flag...
  → Querying Vertex AI Search for tool updates...
  → Querying API Hub for A2A agent status changes...

Coding Agent: Diff detected — 2 changes:
  1. body-shop-a2a upgraded from v2.3 → v2.4 (new capability: "parts-tracking")
  2. tf-ecs-fargate module updated from v2.1.0 → v2.2.0 (security patch)

Coding Agent: Updated files:
  → app-blueprint.md — §5 body-shop-a2a version updated
  → app-blueprint.json — regenerated from updated .md
  → design_contract.json — updated tool versions

No structural changes. Migration phases unchanged.
```

*End of Appendix — Brownfield Developer Guide*
