# AgentCatalyst Brownfield — Developer Guide

*Get from "I need to modernize this legacy app" to a production-ready target-state blueprint plus generated BFF code, IaC, and CI/CD pipelines in under one working day.*

*Canonical name: **AgentCatalyst Brownfield**. Preset: `agentcatalyst-brownfield`.*

---

### Document set

| Document | Filename | Covers |
|---|---|---|
| Architecture | `csa-tsa-speckit-architecture.md` | **WHY** — design decisions, Blueprint Advisor internals, peripheral systems |
| **This document** | `csa-tsa-speckit-developerguide.md` | **HOW** — step-by-step workflow, templates, examples |
| Operating Playbook | `csa-tsa-speckit-operating-playbook.md` | **PROCEDURES** — operations, governance, onboarding |

### Related core AgentCatalyst documents

| Core document | Filename | Consult for |
|---|---|---|
| Core Developer Guide | `agentcatalyst-archetype-agnostic-developer-guide.md` | Greenfield workflows (§2–§3), spec signal words (§4), app-blueprint.md schema (§5), confidence scores (§8), troubleshooting (§14) |
| Core Architecture | `agentcatalyst-architecture-archetype-agnostic.md` | Base Blueprint Advisor MCP design (Layer 2), OAuth 2.1 + Entra ID authentication (Layer 2 Security), IaC generation via GitHub MCP Server (Layer 3), EvalOps three-layer lifecycle (Layer 4) |
| Core Operations Runbook | `agentcatalyst-operations-runbook-both-options.md` | OAuth 2.1 / Entra ID troubleshooting (§9), Governance Guardian operations (§10), Governance Guardian wire format (§10a), MCP tool wire format (§1a) |
| Governance Guardian Extension | `governance-guardian-architecture.md` | `/catalyst.assess` design, assessment flow, scorecard format, `recordTechDebt` gate, tech debt registry |
| app-blueprint.md Template | `app-blueprint-md-template-and-fnol-example.md` | 18-section template structure, FNOL reference example, workspace file layout |

---

## Table of Contents

1. [Quick Start](#1-quick-start-tldr)
2. [Prerequisites](#2-prerequisites)
3. [One-Time Setup](#3-one-time-setup)
4. [Workflow Overview](#4-workflow-overview)
5. [`/speckit.constitution` — Versioned Dual Constitution](#5-speckitconstitution--versioned-dual-constitution)
6. [`/speckit.specify` — Diagram Extraction and Spec Pre-fill](#6-speckitspecify--diagram-extraction-and-spec-pre-fill)
7. [Spec Template (full)](#7-spec-template-full)
8. [Worked Example: `spec.md`](#8-worked-example-specmd)
9. [`/speckit.plan.draft` + `/speckit.plan.review`](#9-speckitplandraft--speckitplanreview)
10. [Plan Template (full)](#10-plan-template-full)
11. [Worked Example: `plan.md`](#11-worked-example-planmd)
12. [`/catalyst.blueprint`](#12-catalystblueprint)
13. [Reviewing the Blueprint and Design Contract](#13-reviewing-the-blueprint-and-design-contract)
14. [`/catalyst.generate`](#14-catalystgenerate)
15. [`/catalyst.refresh` — Keeping Contracts Alive](#15-catalystrefresh--keeping-contracts-alive)
16. [Custom Agent & Prompt Files](#16-custom-agent--prompt-files)
17. [Quality Self-Checks](#17-quality-self-checks)
18. [Common Failure Modes & Fixes](#18-common-failure-modes--fixes)
19. [FAQ](#19-faq)

---

## 1. Quick Start (TL;DR)

```bash
# 1. Install preset (one-time)
specify preset add agentcatalyst-brownfield

# 2. Initialize in your legacy app's repo
cd /path/to/legacy-app-repo
specify init --here --preset agentcatalyst-brownfield --integration copilot

# 3. In VSCode, Agent mode, Claude Opus 4.6:
/speckit.constitution       # confirm enterprise principles (one-time per project)
/speckit.specify            # diagram extraction → spec.md pre-fill → elicitation
/speckit.plan.draft         # first-pass r-factor + cutover per integration
/speckit.plan.review        # async EA/architect review of the plan
/catalyst.blueprint         # async: start → poll (progress in chat) → retrieve blueprint + contract
# review blueprint, contract, diagrams
/catalyst.assess            # governance assessment → scorecard + findings (fix showstoppers → re-assess)
/catalyst.generate          # governance gate (recordTechDebt → stop/resume) + brownfield-aware code + IaC

# Later (before every PR if contract is stale):
/catalyst.refresh           # re-run advisor, diff contract, return to LIVE
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
gemini skills install github.com/company/agentcatalyst-skills --scope user
```

### Per-project initialization

```bash
cd /path/to/legacy-app-repo
specify init --here --preset agentcatalyst-brownfield --integration copilot
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
│   ├── catalyst.blueprint.prompt.md
│   ├── catalyst.assess.prompt.md
│   ├── catalyst.generate.prompt.md
│   └── catalyst.refresh.prompt.md
├── agents/
│   └── csa-extractor.agent.md           ← diagram extractor agent
├── instructions/
│   └── csa-tsa-conventions.instructions.md
└── copilot-instructions.md

memory/
├── constitution-enterprise.md           ← read-only, versioned with preset
└── constitution-project.md              ← editable, validated against enterprise
```

Verify: in Copilot Chat, Agent mode, type `/` and confirm `speckit.constitution`, `speckit.specify`, `speckit.plan.draft`, `speckit.plan.review`, `catalyst.blueprint`, `catalyst.assess`, `catalyst.generate`, `catalyst.refresh` all appear.

---

## 4. Workflow Overview

| Step | Command | What happens | Time |
|---|---|---|---|
| 1 | `/speckit.constitution` | Confirm enterprise principles (one-time per project) | 5 min |
| 2 | `/speckit.specify` | csa-extractor parses diagram → pre-fills spec.md → elicits details | 30 min |
| 3 | `/speckit.plan.draft` | Developer first-pass: r-factor + cutover per integration | 30 min |
| 4 | `/speckit.plan.review` | Async EA/architect review with structured comments | 1–3 days |
| 5 | `/catalyst.blueprint` | Async: start → poll (progress in chat) → retrieve | 1–30 min |
| 6 | Review | Review blueprint, contract, diagrams | 30 min |
| 6a | `/catalyst.assess` | Governance assessment → scorecard + findings (iterative) | 1–5 min |
| 7 | `/catalyst.generate` | Governance gate + brownfield-aware skills generate code + IaC + pipelines | 5–10 min |
| 8 | Developer work | Review, refine, business logic, tests, commit | 2–4 hours |
| 9 | `/catalyst.refresh` (if needed) | Re-verify contract freshness before PR/deploy | 2 min |

The plan review step (4) is async — you don't block waiting. Continue with other work or other integrations. The reviewer leaves comments; you resolve them before step 5.

→ *Architecture §6 covers the 10-stage flow from the architectural perspective.*

---

## 5. `/speckit.constitution` — Versioned Dual Constitution

→ *Architecture §13 covers the versioning model. Operating Playbook §2.6 covers enterprise constitution governance.*

Run once per project:

```
/speckit.constitution
```

AgentCatalyst Brownfield uses a **dual-file constitution**:

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

## 6. `/speckit.specify` — Diagram Extraction and Spec Pre-fill

→ *Architecture §7 covers the CSA Agent handoff boundary and diagram parsing rules.*

This is the brownfield-aware override of Spec Kit's default `/speckit.specify`. The CSA Agent (a separate upstream system) has already produced an accurate CSA diagram and placed it in your workspace. The coding agent's job is to extract integration points from that diagram and pre-fill `spec-template.md`.

### 6.1 Before you run it

Confirm your CSA diagram is in the workspace. Supported formats: `.drawio`, `.drawio.xml`, `.mmd`, `.mermaid`. If you don't have a diagram yet, return to the CSA Agent workflow first — `/speckit.specify` requires a diagram as input.

### 6.2 Run it

```
/speckit.specify
```

### 6.3 What the agent does

1. **Scan.** Finds `*.drawio`, `*.drawio.xml`, `*.mmd`, `*.mermaid` files in the workspace. If multiple, asks which to use.
2. **Parse.** Extracts components (nodes), integrations (edges), cloud boundaries (group containers), and protocol hints (edge labels).
3. **Cluster.** Groups edges by source/target and assigns INT-001, INT-002, ... IDs.
4. **Pre-fill.** Populates the integration blocks of `spec-template.md` with what the diagram revealed.
5. **Elicit.** For fields the diagram cannot reveal, batches questions per integration and asks you. **It will not guess** — it leaves `TODO:` markers if you decline to answer.
6. **Quality check.** Runs the brownfield quality self-check (§17) and reports failures.
7. **Write.** Saves `spec.md` to your repo root.

### 6.4 Setting realistic expectations

Real enterprise diagrams rarely have well-labeled edges like `BFF -->|HTTPS+mTLS| Apigee`. Most edges are unlabeled or labeled vaguely ("calls", "sends data"). The extractor will produce `TODO:` markers for protocol and auth details it cannot infer. This is by design — leaving a gap is better than guessing wrong. Expect ~40–60% of spec fields to be auto-populated from a typical diagram; the rest come from your answers during elicitation.

### 6.5 Example interaction

```
Agent: Found 1 diagram: claims-portal-csa.drawio.xml. Parsing...
Agent: Identified 4 integration edges crossing system boundaries:
       - INT-001: User browser → MPA (UI rendering)
       - INT-002: MPA → APIC → Domain API (sync REST)
       - INT-003: MPA → IBM MQ (async)
       - INT-004: IBM MQ → SQS bridge → downstream (async)

       Should INT-003 and INT-004 be treated as one integration or two?

You: One integration — INT-003 is the MPA producing to MQ, INT-004 is the bridge.
     Treat it as one: MPA → MQ → SQS → downstream app.

Agent: OK, merged as INT-003. Now I need details the diagram doesn't carry.

       For INT-001 (UI rendering):
       - What is the criticality tier? [Tier 1 / 2 / 3]
       - What is the data classification?
       - What is the current p95 page load latency?
       - What is the acceptable downtime during cutover?

You: Tier 2 · Confidential PII · p95 < 2s · 15 min after-hours

Agent: [continues per integration]
Agent: spec.md written. Quality self-check: 10/10. Ready for /speckit.plan.draft.
```

### 6.6 No diagram available

If `/speckit.specify` finds no diagram files, it reports the error and directs you to the CSA Agent workflow. AgentCatalyst Brownfield does not perform source-code scanning or structured interviews — that is the CSA Agent's responsibility.

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

## 12. `/catalyst.blueprint`

→ *Architecture §9 covers the async MCP Tasks design and the 4-stage internal pipeline.*

> **First-time authentication:** The first time you run `/catalyst.blueprint` or `/catalyst.assess`, your coding agent opens a browser for company SSO login (Microsoft Entra ID, OAuth 2.1). After authenticating once (including MFA), tokens are cached securely in your OS keychain. Subsequent commands use silent token refresh — no browser popup. Both the Blueprint Advisor and Governance Guardian share the same authentication. See Architecture Document §17.2 for the full OAuth 2.1 flow.

```
/catalyst.blueprint
```

The Blueprint Advisor uses the **MCP Tasks async protocol** because VS Code Copilot enforces a hard 10–15 second timeout on MCP tool calls, and the internal pipeline can take 1–30 minutes depending on integration count. Instead of one blocking call, three fast MCP tools work together:

**What you see in the Chat pane:**

```
You: /catalyst.blueprint

Agent: Blueprint generation started (task abc-123). Checking progress...
Agent: Stage ④: substitution — 4 integrations resolved ✓
Agent: Stage ⑤: pattern retrieval for INT-001...
Agent: Stage ⑤: pattern retrieval for INT-003 (cross-cloud)...
Agent: Stage ⑤: composition validation ✓ (14 rules checked)
Agent: Stage ⑥: ADR compliance — 4 integrations passed ✓
Agent: Stage ⑦: assembling blueprint + contract + diagrams...
Agent: Blueprint ready. Writing app-blueprint.md and design_contract.json
       to your workspace. Review the 4 Mermaid diagrams inline.
```

**What happens under the hood:**

1. The prompt file calls `blueprint_start` with your spec + plan as JSON. The MCP server validates the input, creates a background task, and returns a `taskId` — all within 2 seconds.
2. The prompt file polls `blueprint_status(taskId)` every 10 seconds. Each poll returns the current pipeline stage and a progress message. The agent reports these to you in the Chat pane.
3. The background job (Cloud Run Jobs, no timeout constraint) runs the 4-stage pipeline: ④ context-filtered substitution → ⑤ semantic pattern retrieval + LLM composition → ⑥ ADR compliance check → ⑦ blueprint + contract + diagram assembly.
4. When the poll returns `status: "completed"`, the prompt file calls `blueprint_result(taskId)` to retrieve the output and writes all files to your workspace:
   - **`app-blueprint.md`** — PRIMARY artifact. Human-readable structured markdown (18 sections). You edit THIS file.
   - **`app-blueprint.json`** — DERIVED artifact. Machine-readable JSON generated from `.md` by `assemble_blueprint`. Consumed by `/catalyst.generate`. **Never edit this file directly** — it's regenerated from `.md` automatically.
   - **`design_contract.json`** — Design contract with provenance, attestations, migration phases.
   - **Diagram files** — `.eraser` (Eraser.io VSCode extension), `.drawio.xml` (Draw.io extension), `.svg` (Canva import), `.png` (auto-rendered, inline in markdown).

If anything fails — substitution unresolved, ADR rejected, composition invalid — the poll returns `status: "failed"` with a structured error. You get the same actionable error messages as before; they just arrive via the polling mechanism.

**Timing:** For the reference case (4 integrations), expect 2–5 minutes. For a complex app with 15 integrations, expect 15–30 minutes. You can continue working in other files during the poll — the agent will notify you when the blueprint is ready.

**If the task takes too long (>30 minutes):** See §18 FM-9.

---

## 13. Reviewing the Blueprint and Design Contract

→ *Architecture §9.6 provides the full design contract schema.*

**Editing diagrams — choose your tool:** Your workspace contains 4 formats per diagram. Edit whichever you prefer — the others are re-rendered when `assemble_blueprint` runs (auto-called by `/catalyst.generate` if `.md` changed):

| Tool | VSCode Extension | File to open |
|---|---|---|
| **Eraser.io** | `eraser.io` extension | `*.eraser` — live visual editor |
| **Draw.io** | `hediet.vscode-drawio` extension | `*.drawio.xml` — full draw.io editor |
| **Canva** | Browser / desktop app | Import `*.svg` — edit visually, export back |
| **Mermaid** | Built-in VSCode preview | Edit inline in `.md` §14 |

Check in this order:

1. **Lifecycle state.** Should be `LIVE`.
2. **Confidence per integration.** `< 0.85` → read `alternatives:`.
3. **`requires_review` flags.** Any present → do not run `/catalyst.generate`. Fix spec or pick alternative.
4. **Phase-0 entries.** Cross-cloud plumbing steps? Coordinate with external teams now.
5. **ADR attestations.** Match EA expectations? Surprises → investigate.
6. **Tech substitutions.** `source_tokens` → `target_tokens` correct?
7. **Migration phases.** Ordering and durations correct?
8. **IaC module versions.** Current?

---

## 13a. `/catalyst.assess` — Governance assessment

→ *Governance Guardian Architecture Extension covers the full assessment flow, solution package schema, scorecard format, and MCP tool definitions.*

After reviewing the blueprint and design contract, run the governance assessment before generating code:

```
/catalyst.assess
```

The coding agent reads `app-blueprint.md` (NOT `app-blueprint.json` — governance assesses the human-readable architecture, not the machine-readable JSON) and extracts all 7 artifact types by section header — the TSA component diagram PNG from §4, HA/DR views from §13, sequence diagrams from §14 (inline mermaid), NFRs from §10, architecture decisions log from §11, tech stack from §12, and patterns from §2 — packages them as an ephemeral solution_package (transport JSON, not the `.json` file), and sends to the Governance Guardian MCP Server via async MCP Tasks (same pattern as Blueprint Advisor). The `app-blueprint.json` file is untouched during governance.

You see progress in the Chat pane: "Evaluating architecture compliance...", "Checking pattern adherence...", "Scoring HA/DR readiness...". When complete, you receive a scorecard (7 categories, 0–100 each) and findings (showstopper / high / medium / low).

**If showstoppers:** Fix them (e.g., add cross-region DR per ADR-205), then re-run `/catalyst.assess`. Repeat until no showstoppers.

**If no showstoppers:** Proceed to `/catalyst.generate`. Remaining findings will be recorded as tech debt.

---

## 14. `/catalyst.generate`

→ *Architecture §14 lists every brownfield-specific skill update.*

```
/catalyst.generate
```

**Governance gate (Step 0):** Before generation runs, the coding agent calls `recordTechDebt` on the Governance Guardian MCP Server. If showstoppers remain → BLOCKED. If no showstoppers → remaining findings recorded as tech debt, generation proceeds. If no assessment exists → warning with skip option.

**Brownfield-aware generation (Steps 1–18)** produces:

- **Application code** — BFF with feature-flag scaffolding for strangler-fig, dual-publish config for MQ→SQS, Apigee client with circuit breaker
- **IaC** — Terraform generated via `company-terraform` skill: reads company module repos via **GitHub MCP Server** (`variables.tf`, `outputs.tf`), maps blueprint fields to module variables deterministically, generates compliant Terraform referencing company modules (never raw `aws_*` resources). Pattern repos provide the scaffold; service modules provide building blocks.
- **CI/CD** — Harness pipeline with `/catalyst.refresh` gate before deploy
- **Runtime compliance** — AWS Config rules generated from `adr_attestations[]`
- **Transition artifacts** — feature-flag configs, dual-publish toggle, Phase-0 checklist

→ *Architecture §12 covers runtime compliance verification.*

---

## 15. `/catalyst.refresh` — Keeping Contracts Alive

→ *Architecture §11 covers the full lifecycle design.*

### 15.1 When you need it

Your design contract goes **STALE** when any peripheral store changes after generation (new ADR ratified, substitution table updated, IaC module version bumped). The pre-commit hook detects this and warns you. After 30 days stale, the contract becomes **EXPIRED** and all actions are blocked.

### 15.2 Run it

```
/catalyst.refresh
```

The agent re-runs the Blueprint Advisor against your existing spec/plan and shows a diff:

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
- `/catalyst.refresh` is required before every PR (pre-commit hook enforces)
- `/catalyst.refresh` is required before every deploy (Harness pipeline gate enforces)
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

**Diagnosis:** No `.drawio`, `.drawio.xml`, `.mmd`, or `.mermaid` files in the workspace.
**Fix:** The CSA Agent (upstream, separate system) must produce the diagram first. Return to the CSA Agent workflow, then re-run `/speckit.specify` once the diagram is in the workspace. → *Architecture §7 covers the handoff boundary.*

### FM-2: Tech substitution unresolved

**Diagnosis:** Table doesn't have your `(source_tech, r_factor, context)`.
**Fix:** File `AGENTCATALYST-SUBSTITUTIONS` ticket. → *Operating Playbook §5, §11.*

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
**Fix:** Run `/catalyst.refresh`, review diff, accept changes. → *§15.*

### FM-8: Constitution contradiction

**Diagnosis:** Pre-commit hook blocks with specific enterprise rule ID.
**Fix:** Remove or reword the conflicting project rule in `constitution-project.md`. → *§5.*

### FM-9: Blueprint task running too long (>30 minutes)

**Diagnosis:** `blueprint_status` keeps returning `working` for more than 30 minutes. The most common cause is a large integration count (>10) combined with slow Vertex AI Search responses or a complex composition-validation pass.
**Fix:** Cancel the task and simplify. Common strategies: split the spec into two batches (first batch: the 5 highest-priority integrations; second batch: the rest), or reduce ambiguity in integration intent paragraphs so pattern retrieval resolves faster. If the problem persists, file an `AGENTCATALYST-ADVISOR` ticket — platform engineering will investigate which pipeline stage is the bottleneck. → *Architecture §9.3.2 covers task lifecycle.*

---

## 19. FAQ

**Q: Can I skip the diagram extraction and write spec.md manually?**
A: Yes. Write your own `spec.md` conforming to the template and proceed to `/speckit.plan.draft`. You lose the diagram-based pre-fill but are not blocked.

**Q: What if my plan review takes too long?**
A: The review is async — work on other things while waiting. If your reviewer is unresponsive, escalate in `#agentcatalyst`. Solo-drafted plans are permitted but the design contract records the review status, and acceptance telemetry shows solo plans have ~20% higher revision rates at PR.

**Q: Can I edit the blueprint and skip `/catalyst.blueprint`?**
A: Yes. The coding agent only needs `app-blueprint.md` and `design_contract.json`. You lose AI-guided recommendation and ADR attestation.

**Q: How do I handle a multi-app modernization?**
A: One `spec.md` and `plan.md` per target service. Each gets its own blueprint and generate invocation.

**Q: What about Visio files?**
A: Convert to drawio first (draw.io: File → Import). Native Visio support is on the roadmap.

**Q: What happens when Claude Opus 4.6 disappears?**
A: The prompt file's model array falls back automatically to Opus 4.7 then Sonnet 4.6. Quality degrades ~5%. → *Operating Playbook §9.*

**Q: How often should I run `/catalyst.refresh`?**
A: At minimum before every PR. For long-lived projects, run weekly as a hygiene check.

---

*End of developer guide.*

*→ Architecture: `csa-tsa-speckit-architecture.md`*
*→ Operating Playbook: `csa-tsa-speckit-operating-playbook.md`*
