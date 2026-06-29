# SDLC Accelerators Brownfield — Operating Playbook

*Procedures for platform engineering and the EA office to build, publish, operate, and evolve the SDLC Accelerators Brownfield Spec Kit preset and its supporting Solution Accelerator.*

*Canonical name: **SDLC Accelerators Brownfield**. Repository: `sdlc-accelerators-brownfield-preset`.*

---

### Document set

| Document | Filename | Covers |
|---|---|---|
| Architecture | `csa-tsa-speckit-architecture.md` | **WHY** — design decisions, Solution Accelerator internals |
| Developer Guide | `csa-tsa-speckit-developerguide.md` | **HOW** — step-by-step workflow, templates, examples |
| **This document** | `csa-tsa-speckit-operating-playbook.md` | **PROCEDURES** — operations, governance, onboarding |
| Governance Guardian | `governance-guardian-architecture.md` | **GOVERNANCE** — `/accelerator.assess` design, EA assessment flow, `recordTechDebt` gate, tech debt registry |

### Related core SDLC Accelerators documents

| Core document | Filename | Consult for |
|---|---|---|
| Core Architecture | `sdlc-accelerators-architecture-archetype-agnostic.md` | Base Solution Accelerator design (Layer 2), OAuth 2.1 + Entra ID authentication (Layer 2 Security), IaC generation via GitHub MCP Server (Layer 3), overlay skill architecture (Layer 3), EvalOps (Layer 4) |
| Core Developer Guide | `sdlc-accelerators-archetype-agnostic-developer-guide.md` | Greenfield workflows (§2–§3), spec signal words (§4), app-blueprint.md schema (§5), `/accelerator.assess` (§2.7a), governance gate (§2.8) |

---

## Table of Contents

1. [Ownership & SLOs](#1-ownership--slos)
2. [Building & Publishing the Preset](#2-building--publishing-the-preset)
3. [Pattern Catalog Operations](#3-pattern-catalog-operations)
4. [ADR Constraint Store Operations](#4-adr-constraint-store-operations)
5. [Tech Substitution Decision Table Operations](#5-tech-substitution-decision-table-operations)
6. [Tool Registry Operations](#6-tool-registry-operations)
7. [IaC Module Registry Operations](#7-iac-module-registry-operations)
8. [Solution Accelerator — Deploy, Scale, Observe](#8-solution-accelerator--deploy-scale-observe)
9. [Total Cost of Ownership](#9-total-cost-of-ownership)
10. [Model Availability Management](#10-model-availability-management)
11. [Acceptance Telemetry Pipeline](#11-acceptance-telemetry-pipeline)
12. [Escalation Queues](#12-escalation-queues)
13. [Incident Response](#13-incident-response)
14. [Governance Cycle](#14-governance-cycle)
15. [Onboarding a New LOB](#15-onboarding-a-new-lob)

---

## 1. Ownership & SLOs

| Component | Owner | SLO |
|---|---|---|
| Spec Kit preset (publishing, version cuts) | Platform engineering | New version every 4 weeks; hotfix within 24h |
| Solution Accelerator MCP Server (Cloud Run + Jobs) | Platform engineering | 99.5% API availability; pipeline p95 < 5 min (4 integrations) |
| Pattern Catalog (Vertex AI Search) | EA office (content) + Platform eng (corpus) | New pattern within 5 business days of ADR approval |
| ADR Constraint Store + Rule Authoring UI | EA office (rules) + Platform eng (UI + infra) | Rules effective within 1 business day |
| Tech Substitution Decision Table + UI | EA office (decisions) + Platform eng (table + UI) | Emergency entry within 5 business days |
| Tool Registry (Apigee API Hub) | Platform engineering | Existing SDLC Accelerators SLA |
| Runtime compliance (AWS Config rules) | Platform engineering | Rules deployed alongside application |
| IaC Module Registry | Platform engineering | Updates within 2 business days of provider-version cut |

---

## 2. Building & Publishing the Preset

→ *Architecture §2 covers the Spec Kit framework relationship and version governance.*

### 2.1 Preset repo structure

```
github.company.com/platform/sdlc-accelerators-brownfield-preset/
├── preset.yml                        ← manifest (pinned speckit_version)
├── templates/
├── prompts/                          ← rendered per agent integration
├── agents/
├── instructions/
├── memory/
│   ├── constitution-enterprise.md    ← versioned, read-only in project repos
│   └── constitution-project-template.md
├── scripts/
│   └── package_blueprint_request.py
├── tests/
│   ├── fixtures/                     ← sample drawio + expected spec output
│   └── e2e/
└── CHANGELOG.md
```

### 2.2 Release pipeline

| Stage | What | Gate |
|---|---|---|
| Lint | Validate frontmatter in all .prompt.md, .agent.md, .instructions.md | Schema pass |
| Fixture tests | Diagram extractor against test drawio files | Match expected spec fields |
| Compatibility | `specify init` against copilot, claude-code, gemini, cursor | All 4 succeed |
| Spec Kit version | Verify pinned Spec Kit version matches preset.yml | Exact match |
| E2E | Full pipeline against staging Solution Accelerator | Blueprint produced |
| Tag & release | Git tag, publish to internal preset registry | Manual approval |

### 2.3 Spec Kit version governance

→ *Architecture §16 covers the risk assessment and contingency plan.*

The preset pins a specific Spec Kit version in `preset.yml`. Upgrades follow this process:

1. Platform engineering evaluates Spec Kit changelog for breaking changes
2. Runs preset CI against candidate Spec Kit version
3. If pass: updates `preset.yml`, cuts a minor-version preset release
4. If fail: opens issue in `sdlc-accelerators-brownfield-preset` with the incompatibility; activates internal fork if no workaround within 2 weeks

**Fork contingency:** If Spec Kit breaks compatibility and no fix is forthcoming, platform engineering activates the internal fork at `github.company.com/platform/speckit-fork`. The fork is a designated technical-debt item reviewed every governance cycle. Maximum fork lifespan: 6 months; escalate to CTO office if resolution is not in sight.

### 2.4 Versioning

Semantic versioning:
- **Major** — breaking schema changes to spec/plan/contract; coordinated with EA quarterly
- **Minor** — new features, backward compatible
- **Patch** — bug fixes, prompt clarifications

### 2.5 Rollback

1. Tag bad version `state:withdrawn`
2. Mark previous-stable `state:current`
3. Broadcast `specify preset upgrade --force` advisory
4. Post in `#sdlc-accelerators`
5. Open Sev-2 incident

### 2.6 Enterprise constitution governance

→ *Architecture doc Part II §10 covers the dual-file model. Developer Guide §5 covers developer usage.*

`constitution-enterprise.md` is maintained in the preset repo. Changes follow the same release pipeline as the preset itself. Version tag convention: `v<year>Q<quarter>` (e.g. `v2026Q2`). Changes require EA office sign-off.

---

## 3. Pattern Catalog Operations (Vertex AI Search)

→ *Architecture §10.1 covers the schema. Developer Guide §12 covers how the catalog feeds the Solution Accelerator.*

### 3.1 Corpus

Vertex AI Search datastore `pattern-catalog-brownfield`. One document per pattern. Embeddings on `description` and `signals`.

### 3.2 Adding a pattern

1. EA office creates draft pattern document; PR to `pattern-catalog-content` repo
2. CI validates schema (`validate_pattern_schema.py`)
3. EA assigns 3 reviewers: domain SME, security architect, cost reviewer
4. Merge triggers `publish_pattern.yaml` (upload + re-embed)
5. Pattern enters `state: preview` for 30 days
6. Auto-promotes to `state: active` if no quality regression

### 3.3 Updating a pattern

Edits to `description` or `signals` trigger 7-day shadow mode (old + new scored in parallel; divergence reported).

### 3.4 Retiring a pattern

`state: deprecated` for 90 days (Solution Accelerator returns it with `requires_review`), then removed. Acceptance telemetry flags production blueprints still referencing retired patterns.

### 3.5 Quality regression suite

Nightly: ~200 representative spec excerpts → Solution Accelerator → verify expected patterns at confidence ≥ 0.85. Regression failures block preview→active promotion.

### 3.6 Cross-cloud egress pattern

→ *Architecture §15 covers the pattern design.*

The PAT-XCLOUD-001 pattern includes a `phase_0_checklist` and `external_teams_required` fields unique to cross-cloud patterns. When maintaining this pattern, coordinate with GCP-networking and Apigee-platform teams to keep the checklist current (transit methods, cert lifecycle, IP allocation procedures).

### 3.7 CSA Agent diagram quality baseline

→ *Architecture §7 covers the handoff boundary between the CSA Agent and SDLC Accelerators Brownfield.*

During LOB onboarding (§15), assess diagram readiness for the pilot app:
- Does the CSA Agent produce a diagram in a supported format (drawio XML or Mermaid)?
- Are integration edges labeled with protocol/transport hints?
- Are cloud/on-prem boundary groups present?
- Report to LOB lead with the expected spec pre-fill coverage (~40–60% of fields from a typical diagram, balance via elicitation)

---


> **Implementation status:** The ADR predicate interpreter (no-`eval()`, 25-identifier ceiling,
> ≥3/≥3 mandatory rule tests) and the substitution decision-table engine (12-dimension ceiling,
> most-specific-wins) are implemented under `brownfield/src/brownfield/`. This playbook governs the
> human-authored CONTENT (rows and rule predicates) those engines consume.

## 4. ADR Constraint Store Operations

→ *Architecture §10.2 covers the design. Architecture §9.4 covers how rules are evaluated.*

### 4.1 Rule Authoring UI

The EA office uses a browser-based rule authoring UI (`adr-rule-editor`, deployed as Cloud Run in `enterprise-ea-prod`). Features:

- **Grammar-aware editor** with autocomplete for all DSL identifiers
- **"Test this rule" sandbox** — evaluates the rule against 50 curated spec+plan fixtures; shows pass/fail/skip per fixture
- **Conflict detection** — before save, checks for contradictions with all existing rules
- **Version history** with diff view
- **Bulk import/export** for quarterly reviews

The UI writes to AlloyDB via a PostgreSQL connection pool. The Solution Accelerator pipeline reads from AlloyDB.

### 4.2 Predicate DSL governance

→ *Architecture §9.4 covers the DSL grammar.*

**Identifier ceiling: 25.** The DSL currently supports 25 identifiers (source_tech, target_tech, r_factor, criticality, etc.). Adding a new identifier requires:
1. Written justification: why the rule cannot be expressed with existing identifiers
2. Refactor proposal: would a new identifier be better served by a new context dimension on the substitution table (§5) instead?
3. Platform-engineering code change to the interpreter
4. EA office approval

The ceiling is enforced by CI — the interpreter's identifier list is declarative and a PR adding a 26th identifier is blocked.

### 4.3 Mandatory rule unit tests

Every rule ships with ≥3 positive and ≥3 negative test cases in the `adr-constraints-content` repo. Test format:

```yaml
tests:
  - name: "MQ refactor to SQS passes"
    input: { source_tech: "ibm-mq-9.1", target_tech: "aws-sqs", r_factor: "refactor" }
    expected: PASS
  - name: "MQ refactor to Amazon MQ is forbidden"
    input: { source_tech: "ibm-mq-9.1", target_tech: "amazon-mq", r_factor: "refactor" }
    expected: REJECT
```

CI runs all rule tests on every PR. A rule without tests is rejected.

### 4.4 Handling contradictions

CI rejects PRs where a new rule contradicts existing rules. EA office must either reword the scope, supersede the existing rule, or resolve in EA meeting.

### 4.5 Exception handling

ADR exceptions are first-class ADRs (e.g. ADR-101-exception) with project-scoped applicability. Same authoring process, same unit tests. The interpreter checks exceptions before rejecting.

### 4.6 Month-6 rule audit

At month 6 of platform operation, the EA office runs a mandatory consolidation audit:
- Every rule reviewed for clarity and necessity
- Rules with zero firings evaluated for retirement
- Rules with high override rate evaluated for refinement
- DSL identifier usage analyzed; underused identifiers candidates for removal

→ *The governance cycle schedule is in the quarterly review section.*

---

## 5. Tech Substitution Decision Table Operations

→ *Architecture §9.3 covers how the table is consumed. Architecture §10.3 covers the schema.*

### 5.1 Context-filtered design

The Tech Substitution Decision Table is a **context-filtered decision table** with bounded dimensions:

| Column | Type | Example | Required? |
|---|---|---|---|
| `source_tech` | string | `ibm-mq-9.x` | Yes |
| `r_factor` | enum | `refactor` | Yes |
| `criticality` | enum | `tier1/tier2/tier3` | No (wildcard if omitted) |
| `data_size_class` | enum | `small/medium/large` | No |
| `compliance_regime` | set | `[SOX, PCI]` | No |
| `messaging_pattern` | enum | `point-to-point/pub-sub/stream` | No |
| `region_constraints` | set | `[us-only]` | No |
| `partner_constraints` | string | free-text | No |
| `target_tech` | string | `aws-sqs` | Yes (output) |
| `adr_ref` | string | `ADR-205` | Yes (output) |
| `transition_pattern_ref` | string | `PAT-T-007` | No (output) |
| `priority` | int | 100 | Yes (higher wins) |

**Dimension ceiling: 12 context columns.** Adding a 13th requires EA office justification and platform-engineering schema migration. CI enforces the ceiling.

### 5.2 Decision Table Authoring UI

Companion to the ADR rule authoring UI, deployed alongside it. Features:
- **Decision-tree visualization** of existing entries
- **"What would this spec match?" simulator** — paste a spec excerpt, see which row matches
- **Conflict detection** — two entries with same context at same priority
- **Zero-usage dashboard** — entries never matched in production
- **Override-rate dashboard** — entries frequently overridden by developers

### 5.3 Adding a substitution

→ *Developer Guide §18 FM-2 covers the developer-facing experience.*

Trigger: developer files `SDLC-ACCELERATORS-SUBSTITUTIONS` ticket when `map_current_to_target` returns `NOT_FOUND`.

| Step | Owner | SLA |
|---|---|---|
| Triage: reject if out of policy | Platform eng | 1 business day |
| Open follow-up issue in `tech-substitution-content` repo | Platform eng | 1 business day |
| EA office reviews (may require multi-dimensional entry) | EA office | 3 business days |
| Entry added via PR; merge triggers SQL insert | Platform eng | 1 business day |
| **Total** | | **5 business days** |

Emergency entries (Sev-1 modernization blockers): 24h end-to-end.

If the required entry spans multiple context dimensions and can't be represented as a single row, the EA office escalates to a 30-min working session with the requesting team to define the correct decision-tree branch. This is tracked as an explicit ticket, not absorbed into the 5-day SLA.

### 5.4 Quarterly review

Every quarter:
- New entries sanity-checked
- Zero-usage entries flagged for retirement
- High-override entries flagged for refinement
- Dimension usage analyzed; underused dimensions considered for removal

---

## 6. Tool Registry Operations

→ *Architecture §10.4 covers the schema and retrieval behavior.*

MCP servers and A2A agents are indexed in Apigee API Hub with enrichment metadata. The Solution Accelerator's `recommend_architecture` queries the registry filtered by `target_tech` to discover tools matching the integration intent and resolved target technology.

Each tool entry carries: `name`, `purpose`, `mcp_endpoint`, `target_tech_compatibility[]`, `r_factor_relevance[]`, and `lifecycle_state` (preview / active / deprecated / retired). The registry's `target_tech_compatibility` field is what brownfield uses most heavily for filtering. For tools that only exist in target state (e.g. SQS MCP server), set `r_factor_relevance: [refactor, rewrite]` to suppress noise in rehost-only scenarios.

Registration, enrichment metadata curation, deprecation flow, and lifecycle-state transitions follow the standard SDLC Accelerators operations process. New tool registrations require: tool name, MCP endpoint URL, purpose description, target-tech compatibility tags, r-factor relevance tags, and a security review confirming the tool operates within the VPC-SC perimeter.

---

## 7. IaC Module Registry Operations

→ *Architecture §10.5 covers the schema and manifest format.*

The IaC Module Registry is a GitHub repository (`github.company.com/platform/tf-modules`) plus a `manifest.yaml` at the repo root. Each module has its own folder with README, examples, and tests. Versions are cut via Git tags. The manifest indexes modules by path, version, supported resources, DR strategies, regions, required tags, and standard references.

### 7.1 Adding a module

Triggered when a new pattern enters the catalog requiring IaC not currently in the registry.

1. Platform engineering authors the module following the company TF module template
2. PR includes the new entry in `manifest.yaml`
3. CI runs `terraform validate`, `terraform plan` against a fixture, security scans (Checkov), cost estimate (Infracost)
4. Code review by IaC reviewers
5. Merge cuts a `v0.1.0` tag in `state: preview`
6. After 30 days with no security findings, auto-promotes to `state: active`

### 7.2 Updating a module

Semver. Patch and minor versions auto-promote after 7-day soak. Major versions require explicit promotion. The Solution Accelerator pins module versions in the design contract — module updates don't retroactively affect produced blueprints.

### 7.3 Drift detection

Nightly comparison of the manifest's `current` version against what's referenced in production design contracts. Drift triggers notification to affected project teams but no automatic migration. Modules >2 major versions behind receive an advisory in the next governance-cycle agenda.

---

## 8. Solution Accelerator — Deploy, Scale, Observe

→ *Architecture §9 covers the internal design.*

### 8.1 Deployment

The Solution Accelerator has two deployment components:

**MCP API layer** — Cloud Run service `solution-accelerator-api` in `enterprise-platform-prod`. Handles six MCP tools — the three blueprint tools (`blueprint_start`, `blueprint_status`, `blueprint_result`) and the Epic-to-Spec front door (`epic_to_spec_start`, `epic_to_spec_status`, `epic_to_spec_result`; legacy `ingest_epic_*` aliases retained), which fuses the Rally Epic with the CSA architecture.md → canonical spec.md. Min: 2 instances. Max: 10. Concurrency: 80 requests/instance (lightweight queries to AlloyDB via connection pool — 20 PostgreSQL connections per instance via AlloyDB Auth Proxy sidecar). Request timeout: 30 seconds (each call completes in <2s). 2 vCPU, 4 GB memory.

**Background pipeline** — Cloud Run Jobs `solution-accelerator-pipeline` in `enterprise-platform-prod`. Runs the 4-stage pipeline (map → recommend → check → assemble) with no request-timeout constraint. Triggered by Cloud Tasks queue `blueprint-tasks`. 4 vCPU, 8 GB memory per job. Max concurrent jobs: 20.

**Task store** — AlloyDB table `blueprint_tasks` in `enterprise-platform-prod` AlloyDB cluster. Stores task records (taskId, owner_id, status, stage, progress, result). 24-hour retention enforced by hourly Cloud Scheduler cleanup job. Cross-region replication enabled for DR.

Primary region: `us-east1`. DR: `us-west1` (cold standby for API layer, RTO 30 min; task store is multi-region by default).

### 8.2 CI/CD

Pipeline `solution-accelerator-release` (deploys both API layer and pipeline job):

| Stage | Gate |
|---|---|
| Unit tests | 100% pass |
| Integration tests | Against staging Vertex AI Search + ADR Store + Substitution Table |
| Async round-trip test | `blueprint_start` → poll → `blueprint_result` against canonical fixtures; match expected output |
| Contract-schema tests | Schema compatibility |
| **Drain in-flight tasks** | Check AlloyDB for `working` tasks; wait up to 5 min for completion. Cloud Run Jobs retains old revision until all executions complete. |
| Canary deploy (API layer) | 10% traffic, 1 hour, error rate < 0.5% |
| Pipeline job deploy | Deploy new Cloud Run Job revision |
| Full deploy | Manual approval |
| Post-deploy verify | Confirm no tasks remain on old pipeline revision after 1 hour |

**Drain procedure:**
```bash
# Check in-flight tasks before deploying new pipeline revision
psql $ALLOYDB_CONNECTION -c "SELECT task_id, status, created_at FROM blueprint_tasks WHERE status = 'working';"
# If empty, proceed. If not, wait up to 5 minutes or proceed (old revision handles them).
```

### 8.3 Observability

| Signal | SLO |
|---|---|
| API layer availability | 99.5% monthly |
| `blueprint_start` latency p95 | < 2s |
| `blueprint_status` latency p95 | < 500ms |
| `blueprint_result` latency p95 | < 2s |
| Pipeline completion p95 (4 integrations) | < 5 min |
| Pipeline completion p95 (10 integrations) | < 15 min |
| Pipeline error rate | < 0.5% |
| Substitution unresolved rate | < 5% (alert above) |
| Composition failure rate | < 2% (alert above) |
| Task store availability | 99.99% (AlloyDB SLA with cross-region replication) |

Dashboards: `Solution Accelerator — Operational Health` (API latency, pipeline duration, error rate), `Solution Accelerator — Quality` (confidence distributions, reject reasons), `Solution Accelerator — Audit` (per-task attestation log).

### 8.4 Rate limiting

Rate limits apply to `blueprint_start` only (the expensive operation that triggers a pipeline run):

- 10 starts/hour per user
- 200 starts/hour per org
- Exceeded calls return 429 with `Retry-After: 60`

`blueprint_status` and `blueprint_result` are not rate-limited (lightweight AlloyDB queries). Whitelist available for platform-eng operational testing.

### 8.5 Per-task cost breakdown

| Component | Cost |
|---|---|
| Cloud Run API layer (start + ~18 polls + result) | ~$0.002 |
| Cloud Run Jobs (pipeline execution, 4 integrations) | ~$0.01 |
| Vertex AI Search queries (4–8 per task) | ~$0.02 |
| Solution Accelerator Agent · recommend_architecture (stage ⑤ pattern composition) | ~$0.08 |
| Solution Accelerator Agent · create_epic_signal_ledger (Epic front door, when used) | ~$0.04 |
| AlloyDB (task record + result storage, 24h retention) | ~$0.001 |
| Logging + observability | ~$0.005 |
| **Per-task total** | **~$0.12** |

### 8.6 Scaling triggers

| Trigger | Action |
|---|---|
| Pipeline completion p95 > 15 min (4 integrations) | Investigate slow stage; consider Vertex AI Search partitioning |
| Cloud Run Jobs concurrent > 15 sustained 1 hour | Raise max concurrent jobs; investigate queue depth |
| 429 rate on blueprint_start > 1% sustained 1 hour | Raise per-org rate limit after EA approval |
| Task store read latency > 100ms p95 | Investigate AlloyDB query plan and connection pool sizing |

### 8.7 Design contract drift detection

→ *Architecture §11 covers the lifecycle design. Developer Guide §15 covers the `/accelerator.refresh` command.*

A nightly job compares current peripheral-store versions (ADR store, substitution table, IaC manifest) against `staleness_triggers` in all production design contracts. Contracts that would transition to STALE are listed in a report to platform engineering. This is informational — the actual transition happens at pre-commit time in the developer's repo.

### 8.8 Runtime compliance deployment

→ *Architecture §12 covers the design.*

The `company-security` skill generates AWS Config rules from `adr_attestations[]` at `/accelerator.generate` time. These rules are Terraform resources in the generated IaC, deployed by the same Harness pipeline. Post-deploy, AWS Config evaluates continuously. Non-compliant resources trigger CloudWatch alarm → Splunk → platform-engineering pager.

Platform engineering maintains the Lambda functions that back the Config rules in `github.company.com/platform/compliance-lambdas`. One Lambda per attestation class (e.g. `check-no-amazonmq`, `check-apigee-only`, `check-ecs-fargate-only`).

### 8.9 Health checks

| Check | Method | Frequency |
|---|---|---|
| API layer reachable | MCP protocol handshake | 60s |
| `blueprint_start` functional | Golden spec (1 integration) → task created | 3 min |
| Pipeline completion | Golden spec (1 integration) → poll until completed | 3 min |
| `validate_composition` | Known-valid tree | 5 min |
| `assemble_blueprint` | Known selections | 5 min |
| Task Store | AlloyDB `SELECT 1` connection check | 60s |
| Cross-user access blocked | `blueprint_result` with wrong `owner_id` → 403 | 15 min |
| Eraser MCP server reachable | HTTP health check to the Eraser MCP server endpoint | 5 min |
| Diagram rendering | Golden spec → verify `.drawio.xml` + `.png` all generated | 4 hours |

The pipeline completion check uses a lightweight golden spec (1 integration, minimal RAG) that completes in <30 seconds, so a 3-minute interval adds negligible load while ensuring failures are detected within 3 minutes.

**Eraser MCP server failure mode:** If the Eraser MCP server is unreachable, `assemble_blueprint` cannot render `.drawio.xml` + `.png` from the diagram DSLs. Any `.drawio.xml` source files already produced are still valid and editable in the Draw.io VSCode extension (local, no cloud dependency). Rendering resumes when the Eraser MCP server recovers. The blueprint `.md` and `.json` are unaffected — only diagram rendering is blocked.

**`app-blueprint.json` failure modes:**

| Failure | Detection | Resolution |
|---|---|---|
| `.json` out of sync with `.md` | `/accelerator.generate` hash check detects mismatch | Auto-resolved: coding agent calls `assemble_blueprint` to regenerate `.json` from `.md` |
| `.json` corrupted or missing | `/accelerator.generate` fails to parse | Delete `.json`, run `assemble_blueprint` manually — `.md` is always the source of truth |
| `.json` edited directly by developer | Hash mismatch on next `/accelerator.generate` | Auto-resolved: regenerates from `.md` (overwriting manual edits). Warn: never edit `.json` directly |

### 8.10 Cloud Tasks queue configuration

The `blueprint-tasks` queue connects `blueprint_start` (API layer) to the background pipeline (Cloud Run Jobs).

| Setting | Value | Rationale |
|---|---|---|
| Queue name | `blueprint-tasks` | Single queue for all brownfield blueprint pipeline tasks |
| Max dispatches per second | 10 | Matches Cloud Run Jobs max-concurrent |
| Max concurrent dispatches | 10 | Prevents pipeline overload |
| Max retry attempts | 3 | Failed tasks retry with exponential backoff |
| Min backoff | 10 seconds | Allow transient failures to resolve |
| Max backoff | 300 seconds | Cap retry delay at 5 minutes |
| Dead-letter topic | `blueprint-tasks-dlq` (Pub/Sub) | Tasks that fail after 3 retries land here for investigation |

**IAM permissions:**
- API layer service account: `cloudtasks.tasks.create` on `blueprint-tasks`
- Pipeline job service account: invoked by Cloud Tasks push handler
- Platform engineering admin: `cloudtasks.queues.purge` for emergency flush

**Flushing stuck tasks:**
```bash
# View queue state
gcloud tasks queues describe blueprint-tasks --project=$PROJECT

# Purge all pending tasks (emergency only)
gcloud tasks queues purge blueprint-tasks --project=$PROJECT

# After purge, mark corresponding AlloyDB task records as "failed"
psql $ALLOYDB_CONNECTION -c "UPDATE blueprint_tasks SET status='failed', progress_msg='queue_purged' WHERE status IN ('accepted','working');"
```

### 8.11 Task Store (AlloyDB) disaster recovery

→ *Architecture §9.3.3 covers the Task Store schema and tenant isolation.*

The AlloyDB Task Store holds transient async task records with a 24-hour retention. It is **not** a durable data store — all content is derived from the spec/plan inputs and the pipeline output, both of which can be regenerated by re-running `/accelerator.blueprint`.

**Why AlloyDB Task Store DR is lower-priority than Vertex AI Search DR:**
- AlloyDB is a managed, highly available service with a 99.99% SLA and automated cross-region replication
- Task records are ephemeral (24h retention) — no historical data is at risk
- Loss of in-flight tasks is recoverable: the developer re-runs `/accelerator.blueprint`

**Scenario: AlloyDB regional outage**
1. AlloyDB with cross-region replication fails over automatically to the read replica
2. If single-region: API layer returns errors on all task operations
3. Recovery: wait for AlloyDB auto-failover, or promote cross-region read replica
4. Notify developers: "Solution Accelerator temporarily unavailable. Author blueprint manually (Developer Guide, §7) or wait for recovery."
5. Estimated RTO: 0 (auto-failover) or 15–30 minutes (manual promotion)

**Scenario: Task records corrupted**
1. No restore needed — records are transient
2. Developers with `working` tasks see `not_found` on `blueprint_status`
3. Developer re-runs `/accelerator.blueprint`
4. No data loss — spec/plan inputs are in the developer's workspace

### 8.12 Solution Accelerator pipeline tracing scope

The Solution Accelerator background pipeline (4-stage: map → recommend → check → assemble) is traced via **Cloud Logging** (structured logs per pipeline stage) and **Dynatrace APM** (OTel spans for RAG query latency, LLM reasoning time, and end-to-end pipeline duration). Arize Phoenix tracing is for **generated agents at runtime** only — it does not trace the Solution Accelerator pipeline. Platform engineers troubleshooting pipeline performance use Dynatrace, not Phoenix.

---

## 9. Total Cost of Ownership

→ *Architecture §17.4 references this section.*

### 9.1 Full TCO model (annual, at 210-use-case enterprise scale)

| Line item | Annual cost | Notes |
|---|---|---|
| **Solution Accelerator compute** | $13,200 | 10K calls/month × $0.11 × 12 |
| **Vertex AI Search** | $18,000 | 500 patterns, 10K queries/day, embedding recomputation |
| **LLM costs (Opus via Copilot)** | Included in Copilot | Premium requests consumed from org quota |
| **Cloud Run + AlloyDB (Task Store + ADR Store + Substitution Table)** | $9,600 | Solution Accelerator + ADR Store + Substitution Table on consolidated AlloyDB cluster |
| **Rule/Table Authoring UIs** | $24,000 | Cloud Run hosting + initial build amortized over 3 years ($72K build / 3) |
| **EA office curation time** | $150,000 | ~0.75 FTE loaded (patterns, ADRs, substitutions, quarterly reviews) |
| **Platform engineering ops** | $400,000 | ~2.0 FTE loaded (Solution Accelerator, peripherals, preset, CI/CD) |
| **Developer training & onboarding** | $48,000 | 7 LOBs × $6,860 (4-week onboarding × architect + developer time) |
| **Runtime compliance Lambdas** | $6,000 | AWS Config rule execution at scale |
| **Copilot licensing delta** | Variable | Incremental premium-request consumption; depends on tier |
| **Total annual platform TCO** | **~$669,000** | |

### 9.2 Revised ROI at scale

| Metric | Value |
|---|---|
| Per-use-case savings (with SDLC Accelerators Brownfield) | $39,000 (unchanged) |
| Use cases at scale | 210 |
| Gross savings | $8.19M |
| Platform TCO | ~$669K |
| Net savings | ~$7.52M |
| **Revised ROI** | **~11.2×** (vs. original 48× based on compute-only cost) |
| Break-even | ~18 use cases (~month 4) |

The ROI remains compelling at 10.7× but is materially different from the 48× in the original ELT deck. Recommend updating the ELT deck with these figures.

### 9.3 Cost sensitivities

- EA FTE allocation is the largest single cost. If curation quality drops due to understaffing, downstream quality degrades (pattern accuracy, ADR rule coverage, substitution-table completeness).
- Platform engineering FTE is the second-largest cost. If preset quality or Solution Accelerator uptime is de-prioritized, developer rework time increases proportionally.
- LLM costs may change if Copilot adjusts premium-request multipliers or model pricing.

---

## 10. Model Availability Management

→ *Developer Guide §2.2 covers developer-facing setup.*

### 10.1 Tenant policy

Business/Enterprise: enable Claude Opus 4.6 policy in Copilot admin. Confirm first business day of each month.

### 10.2 Fallback chain

All prompt/agent files use: `model: ['Claude Opus 4.6', 'Claude Opus 4.7', 'Claude Sonnet 4.6']`.

### 10.3 Monitoring

Daily synthetic job runs a sample Epic + CSA architecture.md fixture through `/accelerator.epic-to-spec` (and the drawio fallback through `/speckit.specify`). Output compared against canonical expected result. Drift > 10% triggers P3 investigation.

### 10.4 Communication

If Opus 4.6 is removed from tenant: advisory in `#sdlc-accelerators` within 1 hour. No developer action needed (fallback is automatic).

---

## 11. Acceptance Telemetry Pipeline

→ *Architecture §17.3 covers the feedback loop.*

### 11.1 Captured signals

| Signal | Source |
|---|---|
| Blueprint generated | MCP server logs |
| Plan review status (solo vs. reviewed) | plan.md `review_status` field |
| Developer modified blueprint | Git diff at generate time |
| **Modification reason** (per field) | **PR-template dropdown** |
| `requires_review` flags addressed | Edit count |
| ADR attestation overridden at PR | PR comment |
| Project reached prod | Harness events |
| Runtime compliance violation | AWS Config events |

### 11.2 Structured modification reasons

The PR template includes a mandatory dropdown per blueprint field edit:

| Reason | What it means for quality |
|---|---|
| Advisor wrong | Catalog/table needs refinement |
| New information | Developer learned something post-blueprint |
| Scope change | Business decision changed |
| Mistake (reverted) | Noise — exclude from quality metrics |
| Preference | Developer preference, not advisor error |

Without this categorization, quality metrics conflate advisor errors with developer-side noise. The EA office uses "advisor wrong" signals to prioritize catalog and rule refinements.

### 11.3 Quality metrics

| Metric | Target |
|---|---|
| Acceptance rate (Blueprint unchanged) | > 70% |
| Major modification rate (>30% fields) | < 10% |
| `requires_review` rate | < 15% |
| ADR override rate | < 5% |
| Pattern accuracy (post-cutover survey) | > 85% |
| Solo-plan revision rate at PR | < 30% |
| Reviewed-plan revision rate at PR | < 10% |
| Runtime compliance violation rate | < 1% |
| `blueprint_start` latency p95 | < 2 seconds |
| Pipeline completion p95 (4 integrations) | < 5 minutes |
| Pipeline completion p95 (10 integrations) | < 15 minutes |
| Task status transitions in correct order | 100% |
| Failed tasks return structured error (not hang) | 100% |

Regression tests should include a **deliberately malformed spec** golden test case to verify the pipeline produces a `failed` task with a structured error rather than hanging indefinitely.

### 11.4 Dashboards

- `Acceptance Telemetry — LOB View`
- `Acceptance Telemetry — Catalog Quality`
- `Acceptance Telemetry — ADR Effectiveness`
- `Acceptance Telemetry — Plan Review Impact` (solo vs. reviewed plan outcomes)

---

## 12. Escalation Queues

JIRA project: `SDLC-ACCELERATORS`.

| Queue | Purpose | SLA |
|---|---|---|
| `SDLC-ACCELERATORS-SUBSTITUTIONS` | Missing tech substitutions | 5 business days |
| `SDLC-ACCELERATORS-PATTERNS` | Wrong pattern, missing pattern | EA review (quarterly governance cycle) |
| `SDLC-ACCELERATORS-ADR` | ADR exception, rule clarification | EA review (quarterly governance cycle) |
| `SDLC-ACCELERATORS-TOOLS` | Tool registry gaps | 1–2 weeks |
| `SDLC-ACCELERATORS-IAC` | IaC module gaps/bugs | 2 business days |
| `SDLC-ACCELERATORS-ADVISOR` | Solution Accelerator bugs/outages | Sev-driven |
| `SDLC-ACCELERATORS-PRESET` | Preset issues (template, prompt, agent) | Sev-driven |

Office hours: EA office Tuesdays 2–3 PM ET. Platform engineering Thursdays 10–11 AM ET.

---

## 13. Incident Response

### 13.1 Severity matrix

| Sev | Definition | Response |
|---|---|---|
| Sev-1 | Advisor down or wrong outputs at scale; LOB blocked | < 30 min, on-call paged |
| Sev-2 | Feature degraded, workaround exists | < 2 hours, on-call notified |
| Sev-3 | Single-LOB or single-feature issue | Next business day |
| Sev-4 | Cosmetic, documentation | Next sprint |

### 13.2 Common Sev-1/2 patterns

| Pattern | Likely cause | Mitigation |
|---|---|---|
| All `blueprint_start` calls fail 5xx | Cloud Run API layer down | Failover to DR region |
| All pipelines stuck in "working" | Cloud Run Jobs quota exhausted or Cloud Tasks queue jammed | Check Cloud Tasks queue depth; flush stuck tasks; scale Jobs quota |
| Task store unavailable | AlloyDB health check failure | AlloyDB has automated cross-region failover; verify instance status; if global outage, engage GCP support |
| All ADR checks reject everything | Bad rule pushed | Roll back latest ADR-content PR |
| All substitutions NOT_FOUND | Postgres issue or schema drift | Verify AlloyDB; automated cross-region failover |
| Confidence collapsed to ~0.5 | Corpus re-indexing or model change | Wait for re-index; verify model |
| Slash commands vanished | Preset registry corruption | Republish last-known-good version |
| Runtime compliance false positives | Config rule Lambda bug | Disable rule; hotfix Lambda |
| Governance Guardian unreachable | Cloud Run health check | Same deployment as Solution Accelerator API layer; check Cloud Run, OAuth, VPC-SC |
| Governance assessment stuck | Cloud Tasks `governance-assess` queue jammed | Flush queue; mark orphaned AlloyDB records as failed |
| recordTechDebt returns unexpected "stop" | Stale assessment with resolved showstoppers | Developer re-runs `/accelerator.assess` to get fresh assessment |

Postmortem: every Sev-1/2 within 5 business days.

---

## 13a. Governance Guardian Operations

→ *Governance Guardian Architecture Extension covers the full design. Core Operations Runbook §10 covers shared operational procedures. Core Operations Runbook §10a covers the MCP wire format for governance tools.*

The Governance Guardian uses the same async MCP Tasks pattern as the Solution Accelerator. It shares the same AlloyDB instance (separate table `governance_tasks`), the same OAuth 2.1 / Entra ID authentication (`sdlc-accelerators.mcp` audience scope), and the same Cloud Run deployment model. See Core Operations Runbook §9 for authentication troubleshooting (Entra ID).

> **Quick OAuth troubleshooting:** If developers report 401 errors on `/accelerator.assess`, the most common cause is expired refresh tokens (>24 hours since SSO login). Resolution: developer closes and reopens VSCode to trigger fresh Entra ID SSO. For JWKS validation failures or 403 Forbidden, see Core Operations Runbook §9 for the comprehensive troubleshooting table.

### Health checks

| Check | Method | Frequency |
|---|---|---|
| API layer reachable | MCP protocol handshake | 60s |
| `assess_start` functional | Golden FNOL solution package → task created | 3 min |
| Assessment completion | Golden solution package → poll until completed | 3 min |
| `recordTechDebt` functional | Known assessment ID → resume/stop signal | 5 min |
| `getAssessmentHistory` functional | Known solution_id → returns history | 5 min |
| EA assessment engine reachable | Health endpoint on EA service | 60s |

### Cloud Tasks queue

| Setting | Value |
|---|---|
| Queue name | `governance-assess` |
| Max dispatches/sec | 10 |
| Max concurrent | 10 |
| Max retries | 3 |
| Dead-letter topic | `governance-assess-dlq` |

### Task Store + Tech Debt Registry

The `governance_tasks` table follows the same 24-hour TTL cleanup as `blueprint_tasks`. The `tech_debt` table is **persistent** — tech debt records are NOT subject to TTL cleanup. They remain until manually resolved.

### EA assessment engine SLA

| Metric | Target | Alert |
|---|---|---|
| Assessment completion p95 | < 60 seconds | > 120 seconds |
| Availability | 99.5% | < 99% |
| False positive rate | < 5% | > 10% |

---

## 14. Governance Cycle

Realistic cadence: **quarterly target with semi-annual fallback.** If the EA office cannot meet quarterly, the cycle shifts to semi-annual with a mid-cycle async checkpoint. Build slack into the schedule and don't gate platform decisions on meetings happening exactly on time.

### Cycle 1 (Weeks 1–2): Pattern Catalog + Cross-Cloud Patterns

- Patterns added/updated/retired (sanity check)
- Zero-usage patterns (retirement candidates)
- Declining-accuracy patterns (refinement candidates)
- Cross-cloud patterns: checklist currency verified with GCP/Apigee teams
- New patterns proposed by LOBs

### Cycle 2 (Weeks 3–4): ADR Constraint Store + Month-6 Audit

- Rules added/updated/retired
- High-override rules (refinement or formal exception)
- Zero-firing rules (retirement candidates)
- DSL identifier usage audit
- **Month-6 consolidation audit** (first-year only): every rule reviewed for clarity

### Cycle 3 (Weeks 5–6): Tech Substitution Table

- New entries sanity-checked
- Zero-usage entries (retirement)
- High-override entries (refinement)
- Dimension usage audit
- Cross-check: new enterprise tech standards → entries needed?

### Cycle 4 (Weeks 7–8): Acceptance Telemetry + TCO Review

- Acceptance rate trend per LOB
- Top modified fields + modification reasons (which "advisor wrong" signals drive what catalog changes?)
- Solo vs. reviewed plan outcome comparison
- Runtime compliance violation trend
- TCO actuals vs. model; revised ROI if materially different

### Output: Quarterly readout

5-slide deck to CIO/CTO office + LOB leads: metrics, top issues, planned changes, investments requested.

### Spec Kit version review

Every governance cycle includes a Spec Kit version assessment: is a new Spec Kit version available? Has it been tested? Should the pin be updated? Is the fork contingency active?

---

## 15. Onboarding a New LOB

### 15.1 Prerequisites (LOB)

- [ ] Copilot Business/Enterprise tenant with Opus 4.6 policy enabled
- [ ] ≥2 champion architects identified
- [ ] LOB ADRs reviewed by EA office (present in global store or scoped locally)
- [ ] Cost-center tagging confirmed
- [ ] Target AWS account(s) provisioned in landing zone
- [ ] Pilot app selected (Tier 2/3, < 10 integrations)

### 15.2 Onboarding sequence (5 weeks)

| Week | Activity | Owner |
|---|---|---|
| 1 | Kickoff workshop: SDLC Accelerators Brownfield workflow using reference case | Platform eng |
| 1 | **CSA Agent diagram quality check** for pilot app (§3.7) | Platform eng |
| 2 | Pilot: developer runs full workflow with platform-eng observing | LOB + Platform eng |
| 2 | Identify gaps: substitutions, patterns, ADRs, scanner analyzers | Both |
| 3 | Platform eng fills gaps (priority-queue jumps) | Platform eng |
| 4 | LOB re-runs pilot end-to-end to generated PR | LOB |
| 4 | Plan review exercise: LOB architect reviews pilot plan | LOB + EA |
| 5 | LOB readout: time saved, quality, blockers | LOB |
| 5 | LOB declared GA for brownfield adoption | Platform eng |

### 15.3 Success criteria

- Pilot app reaches deployable PR in ≤ 1 working day
- ≥ 80% acceptance rate on produced blueprint
- Zero ADR violations at PR review
- LOB champions can run a second pilot independently

### 15.4 Ongoing support

After onboarding: `#sdlc-accelerators` channel, escalation queues, office hours. Monthly check-in for first 6 months with each newly onboarded LOB. Platform engineering commits to a quarterly review of each LOB's acceptance-telemetry dashboard.

---

## Migration Readiness Validation — Troubleshooting

The Solution Accelerator validates brownfield specs for migration readiness before running the RAG pipeline. When teams report "migration plan looks wrong" or "phases don't make sense," check the spec signal quality first.

| Symptom | Likely cause | Resolution |
|---|---|---|
| "blueprint_start returned BLOCK error" | Critical migration signal missing | Read error: CSA completeness (<3 integrations), integration types (<50% classified), data flow direction (<50% marked), or coexistence constraints (0 flags). Fix the specific gap. |
| "Tech Substitution returned no mappings" | CSA has vague technology names | Check each integration: "Oracle 19c" maps to Aurora. "Legacy database" has no mapping. Add specific tech + version for every component. |
| "Phase assignment is wrong — critical system in Phase 1" | Missing criticality ratings | Check: are all integrations rated critical/high/medium/low? Without ratings, phase assignment defaults to alphabetical — which is wrong. Rate by business impact. |
| "Dual-write not generated for bidirectional integration" | Missing coexistence flag | Check: does the bidirectional integration have `coexistence: dual-write`? Missing flag → hard-cutover assumed → data loss risk during migration. |
| "Strangler-Fig proxy routes are incomplete" | Missing API contracts | Check: do external-facing APIs have documented contracts (OpenAPI/WSDL)? Without contracts, the proxy can't route correctly. Document API surface before migration. |
| "Session loss during Phase 1 cutover" | Stateful component not identified | Check: are sticky sessions, server-side state, distributed transactions documented in the spec? Missing → proxy switches without session migration → users lose sessions. |
| "Phase 2 takes too long" | Too many bidirectional integrations in Phase 2 | Review data flow direction: can any bidirectional integrations be split into separate read + write phases? Reducing Phase 2 scope reduces dual-write coexistence duration. |
| "migration_readiness_score < 50" | Multiple BLOCK or WARN signals | Review validation output — each signal includes specific guidance. Fix BLOCKs first (they prevent pipeline execution), then WARNs (they reduce confidence). Target score ≥ 80 before proceeding. |

**Key principle:** Brownfield validation prevents DATA LOSS. Unlike greenfield (where bad architecture is redesignable), brownfield errors affect a RUNNING production system. Invest the time to get the spec signals right before running the Solution Accelerator.

---

*End of operating playbook.*

*→ Architecture: `csa-tsa-speckit-architecture.md`*
*→ Developer Guide: `csa-tsa-speckit-developerguide.md`*

## /accelerator.refresh — Operations Guide

The `/accelerator.refresh` command validates edited files and regenerates derived artifacts. Also auto-triggered by `/accelerator.assess` and `/accelerator.generate` when stale files are detected.

### What /accelerator.refresh Does

| Step | Action | Server resource | Failure mode |
|---|---|---|---|
| 0. validate_spec | Check 8 brownfield 8-signal migration readiness signals (PASS/WARN/BLOCK) | CPU only | BLOCK → abort with guidance |
| 1. Validate Part I | Parse §1-§7 completeness | CPU only | Missing section → WARN |
| 2. .md↔.drawio consistency | Parse .drawio.xml, compare with §5 topology | CPU only | Mismatch → report differences |
| 3. Sync Part II | Generate/update §8-§12 from Part I + API Hub + Tech Sub Table | API Hub, Tech Sub Table | API timeout → use cached defaults |
| 4. Regenerate .json | Parse all 12 sections → JSON | CPU only | Parse error → report line |
| 5. Regenerate diagrams | Eraser MCP render (DSL → .drawio.xml + .png) | Eraser MCP server | Timeout → keep existing diagrams |

### Skip-Refresh Safety

Both `/accelerator.assess` and `/accelerator.generate` auto-detect stale files:
1. Compare .md/.drawio timestamps with .json timestamp
2. If source newer → auto-refresh before proceeding
3. If auto-refresh fails → STOP with error

### Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| "validate_spec BLOCK — missing coexistence flags" | Integration missing dual-read/dual-write/hard-cutover flag | Add coexistence flag to each integration in §5. See Developer Guide "Writing Brownfield Specs That Pass Migration Readiness Validation". |
| "Part I section missing" | Developer deleted governance section | Restore section. All 7 governance sections required. Part II sections auto-regenerate if deleted. |
| ".md↔.drawio mismatch" | Conflicting edits to .md and .drawio | Pick one source: update §5 to match diagram or update diagram to match §5. Re-run refresh. |
| ".json parse error" | Malformed markdown table | Fix table formatting (pipe characters, column alignment). Re-run refresh. |
| "Part II rows not updating for new integration" | Tech Substitution Table lookup failed | Check connectivity. If tech not in table, manually add §8 row. |

