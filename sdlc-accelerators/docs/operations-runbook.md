# SDLC Accelerators — Operations Runbook

**Operational procedures, monitoring, and maintenance for the SDLC Accelerators platform**
*This is a living document maintained by the Platform Engineering team.*

*Applies to: Both GA and agents-cli architecture variants. All procedures in this runbook are platform-level — the Solution Accelerator MCP Server, Vertex AI Search catalogs, telemetry pipelines, and quality engineering processes are identical across variants. Runtime-specific operations (Cloud Run scaling for GA, agents-cli FORBIDDEN command enforcement for agents-cli) are covered in the respective architecture documents.*

### Related Documents

| Document | Filename | Audience | Relationship to this runbook |
|---|---|---|---|
| **SDLC Accelerators Architecture Document** (GA) | `sdlc-accelerators-architecture-archetype-agnostic.md` | Architects | Provides the WHY behind each system this runbook maintains. When you need to understand why the Solution Accelerator MCP Server is designed a certain way, consult the Architecture Document (Layer 2). |
| **SDLC Accelerators Developer Guide** (GA) | `sdlc-accelerators-archetype-agnostic-developer-guide.md` | Developers | Provides the HOW for developers. When a developer reports an issue, this runbook tells you how to diagnose it. The Developer Guide (Section 9 and Section 11) tells developers what information to include in tickets. |
| **This Operations Runbook** | `sdlc-accelerators-operations-greenfield_runbook.md` | Platform engineering | PROCEDURES — wire-level APIs, regression testing, telemetry, tool lifecycle, failure modes, escalation matrix, EvalOps operations |
| **Governance Guardian Architecture Extension** | `governance-guardian-architecture.md` | Architects, EA office | Provides the design for `/accelerator.assess` and `recordTechDebt` governance gate. When Governance Guardian issues arise, consult the extension document for solution package schema, scorecard format, and Tech Debt Registry. |

### Cross-reference map

| This runbook section | Architecture doc section | Developer guide section |
|---|---|---|
| 1. Wire-Level API Calls | Layer 2 — Solution Accelerator MCP Server | Section 2.5 — `/accelerator.blueprint` (async invocation) + Section 5 — Understanding the app-blueprint.md |
| 2. Search Quality Regression | Layer 2 — Solution Accelerator | Section 8 — Reading Confidence Scores |
| 3. Acceptance Telemetry | Layer 2 — Solution Accelerator | Section 9 — When the Solution Accelerator Gets It Wrong |
| 4. Catalog Quality | Layer 2 — Vertex AI Search data stores | Section 4 — Writing Effective Specs |
| 5. Tool Lifecycle | Layer 2 — Tool Registry | Section 11 — Reporting Issues |
| 6. Failure Modes | Layer 2 — Solution Accelerator MCP Server | Section 14 — Troubleshooting |
| 7. Composition Validator | Layer 2 — Pattern composition | Section 6 — Iterating on the Design |
| 8. EvalOps Operations | Layer 4 — EvalOps 3-layer lifecycle | Section 4b — EvalOps Workflow |
| 9. MCP Server Operations | Layer 2 — Solution Accelerator MCP Server | Section 2.5 — `/accelerator.blueprint` (async invocation) |
| 10. Governance Guardian Operations | Governance Guardian Architecture Extension | Section 2.7a — `/accelerator.assess` |
| 11. Apigee Proxy + Workload Identity + API Hub A2A Ops | Layer 3 — Generated from app-blueprint.md + Layer 5 — Runtime | Section 2 — `/accelerator.generate` output |

---

## 1. Wire-Level Vertex AI Search API Calls

> **Architecture context:** The Solution Accelerator MCP Server (see Architecture Document, Layer 2) exposes six MCP tools to the coding agent: `blueprint_start` (async start), `blueprint_status` (poll), `blueprint_result` (retrieve), `refresh` (bidirectional sync), `validate_composition` (deterministic), and `assemble_blueprint` (deterministic). The first three implement the MCP Tasks async pattern — `blueprint_start` creates a background task that runs the Solution Accelerator LlmAgent, the coding agent polls `blueprint_status` for progress, and retrieves the result via `blueprint_result`. Internally, the background pipeline uses three RAG tools to query Vertex AI Search. These RAG tools are NOT exposed to the coding agent.

### Transport security

All communication between the coding agent and the Solution Accelerator MCP Server is encrypted:

| Hop | Protocol | Encryption |
|---|---|---|
| Coding agent → Cloud Run API layer | MCP over HTTPS | TLS 1.3 (Cloud Run default) |
| Cloud Run API layer → AlloyDB Task Store | PostgreSQL wire protocol | TLS 1.3 (AlloyDB enforced) |
| Cloud Run Jobs (pipeline) → Vertex AI Search | gRPC | TLS 1.3 (Google internal) |
| Cloud Run Jobs (pipeline) → Gemini API | HTTPS | TLS 1.3 (Google internal) |

**Spec content in transit:** The developer's `spec.md` and `plan.md` are transmitted as `blueprint_start` parameters over TLS-encrypted connections. Content is stored in the AlloyDB Task Store (encrypted at rest) during pipeline processing and auto-deleted after the 24-hour TTL. Content is NOT logged. Only the spec hash (SHA-256) is captured in telemetry for traceability.

**Data residency:** The Solution Accelerator API layer and background pipeline run in a specific GCP region (configured at deployment). Spec content does not leave this region. Vertex AI Search data stores and the AlloyDB Task Store are co-located in the same region.

**Audit trail:** Every `blueprint_start` call logs: timestamp, authenticated user identity, spec hash, plan hash, task ID, response latency. Every `blueprint_result` call logs: task ID, pipeline duration, result size, completion status. Content is NOT logged. See Section 3 (Acceptance Telemetry) for the full telemetry schema.

### API endpoint format

```
POST https://discoveryengine.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/collections/default_collection/dataStores/{DATA_STORE}/servingConfigs/default_search:search
```

### Request structure (search_patterns example)

```json
{
  "query": "sequential workflow with parallel enrichment and human review",
  "pageSize": 5,
  "queryExpansionSpec": { "condition": "AUTO" },
  "spellCorrectionSpec": { "mode": "AUTO" },
  "contentSearchSpec": {
    "snippetSpec": { "returnSnippet": true, "maxSnippetCount": 3 },
    "summarySpec": {
      "summaryResultCount": 3,
      "includeCitations": true,
      "modelSpec": { "version": "gemini-1.5-flash-001/answer_gen/v1" }
    },
    "extractiveContentSpec": {
      "maxExtractiveAnswerCount": 1,
      "maxExtractiveSegmentCount": 3
    }
  },
  "filter": "metadata.archetype = \"agentic\"",
  "boostSpec": {
    "conditionBoostSpecs": [
      { "condition": "metadata.status = \"production\"", "boost": 0.5 }
    ]
  }
}
```

### Response processing order

1. `results[].document.structData` — structured metadata (name, applicability, composition rules)
2. `results[].document.derivedStructData.snippets` — contextual descriptions
3. `summary.summaryText` — search engine natural language synthesis
4. Confidence scoring: exact metadata match = high, snippet match = medium, summary-only = low

> **Developer Guide context:** Developers see confidence scores in the markdown blueprint (Developer Guide, Section 8). When they report low-confidence results, check the response processing chain above.

### Data store identifiers

| RAG Tool (internal) | Data Store ID | Contents |
|---|---|---|
| `search_patterns()` | `sdlc-accelerators-patterns` | 11 agentic patterns (8 sections each) |
| `search_skills()` | `sdlc-accelerators-skills` | Reusable skills with use_when/do_not_use_when |
| `search_tools()` | `sdlc-accelerators-tools` | MCP servers, A2A Agent Cards, FunctionTool defs |

### Performance

| Metric | Typical | Alert threshold |
|---|---|---|
| RAG query latency (p50) | 200–400ms | > 800ms |
| RAG query latency (p99) | 600–1,200ms | > 2,000ms |
| Results per query | 3–5 | < 1 |
| Cost per query | ~$0.003 | N/A |
| `blueprint_start` latency | < 2 seconds | > 5 seconds |
| `blueprint_status` latency | < 500ms | > 2 seconds |
| `blueprint_result` latency | < 1 second | > 3 seconds |
| Full pipeline (3 RAG + LLM + validate + assemble) | 15–60 seconds | > 120 seconds |

### Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Empty results | Data store not indexed / embedding stale | Re-run ingestion pipeline, verify document count |
| Irrelevant results | Missing/incorrect metadata | Check `metadata.archetype` and `metadata.tags` |
| High RAG latency | Large corpus + complex query | Add `filter`, reduce `pageSize` |
| Permission denied | Missing `discoveryengine.viewer` role | Grant IAM role |
| `blueprint_start` fails | API layer down or AlloyDB unavailable | Check Cloud Run API layer logs; verify AlloyDB status |
| Pipeline stuck in "working" | Cloud Run Jobs quota exhausted or Cloud Tasks jammed | Check Cloud Tasks queue depth; flush stuck tasks |
| `blueprint_result` returns empty | Pipeline failed silently | Check `blueprint_status` for `failed` status with error detail |

---

## 1a. MCP Async Tool Wire Format

> **Architecture context:** Architecture Document, Layer 2 (MCP Tools table). **Developer Guide context:** Developer Guide, Section 2.5 (what the developer sees).

The coding agent calls these three tools via MCP protocol. Platform engineers will see these request/response shapes in Cloud Run API layer logs.

**`blueprint_start` — request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "blueprint_start",
    "arguments": {
      "spec": "<contents of spec.md>",
      "plan": "<contents of plan.md>"
    }
  }
}
```

**`blueprint_start` — response:**
```json
{
  "content": [{
    "type": "text",
    "text": "{\"taskId\": \"a1b2c3d4-e5f6-7890-abcd-ef1234567890\", \"status\": \"accepted\", \"pollInterval\": 10000}"
  }]
}
```

**`blueprint_status` — response (stage values to expect in logs):**
```json
{
  "content": [{
    "type": "text",
    "text": "{\"taskId\": \"a1b2c3d4...\", \"status\": \"working\", \"stage\": \"reasoning\", \"message\": \"LLM reasoning: mapping tools to agents...\"}"
  }]
}
```

Stage values: `accepted` → `searching` → `reasoning` → `validating` → `assembling` → `completed` (or `failed`).

**`blueprint_result` — response (completed):**
```json
{
  "content": [{
    "type": "text",
    "text": "{\"taskId\": \"a1b2c3d4...\", \"status\": \"completed\", \"yaml\": \"<app-blueprint.md content>\", \"confidence_scores\": {...}}"
  }]
}
```

**`blueprint_result` — response (failed):**
```json
{
  "content": [{
    "type": "text",
    "text": "{\"taskId\": \"a1b2c3d4...\", \"status\": \"failed\", \"error\": {\"type\": \"composition_invalid\", \"detail\": \"LoopAgent cannot nest inside ParallelAgent\"}}"
  }]
}
```

---

## 2. Search Quality Regression Suite

> **Architecture context:** See Architecture Document, Layer 2. **Developer Guide context:** Developers experience quality as confidence scores (Developer Guide, Section 8) and incorrect recommendations (Developer Guide, Section 9).

### Golden test suite (30–50 cases)

```
tests/golden/
├── fnol-basic/
│   ├── spec.md, plan.md, expected.yaml, assertions.json
├── fnol-brownfield/
│   ├── ...
└── microservice-order-mgmt/    ← GA variant only
```

### Assertions format

```json
{
  "pattern_selection": { "root_pattern": "coordinator", "must_contain": ["sequential", "parallel"] },
  "tool_assignment": { "bigquery_assigned_to": "enrichment_agent" },
  "skill_discovery": { "must_discover": ["adk-agents"], "min_confidence": "medium" },
  "business_rules": { "severity_classifier_has_rules": true, "rule_count_minimum": 3 },
  "async_lifecycle": {
    "start_latency_max_ms": 2000,
    "first_status_within_ms": 5000,
    "expected_stage_order": ["accepted", "searching", "reasoning", "validating", "assembling", "completed"],
    "completion_max_seconds": 120,
    "result_contains_yaml": true,
    "result_contains_confidence": true
  }
}
```

The `business_rules` assertions verify that business rules pass through from spec to blueprint. When the Solution Accelerator drops rules, the coding agent generates stubs instead of first-draft implementations — a significant quality regression.

The `async_lifecycle` assertions verify the MCP Tasks transport layer — not just the content quality. If the async handoff breaks (e.g., Cloud Tasks enqueue fails silently, AlloyDB writes are delayed, status transitions skip stages), these assertions catch it before developers experience the failure. A **deliberately malformed spec** golden test case should also be included to verify that the pipeline produces a `failed` task with a structured error rather than hanging indefinitely.

### Execution

```bash
python3 scripts/run_regression.py \
  --golden-dir tests/golden/ \
  --mcp-endpoint mcp://solution-accelerator.[company-domain].run.app \
  --output results/$(date +%Y%m%d).json
```

The suite calls the MCP Server via the same async protocol the coding agent uses — `blueprint_start` → poll `blueprint_status` → `blueprint_result` — testing the exact code path developers experience.

### Quality metrics

| Metric | Target | Alert |
|---|---|---|
| Pattern selection accuracy | ≥ 90% | < 85% |
| Tool assignment accuracy | ≥ 85% | < 80% |
| Skill discovery recall | ≥ 90% | < 85% |
| Business rules passthrough | 100% | < 100% |
| Zero-result queries | 0% | > 0% |

### Cadence

| Trigger | Action |
|---|---|
| System prompt change | Full suite |
| Catalog change | Affected cases only |
| MCP Server deployment | Full suite |
| Weekly | Full suite (automated) |

---

## 3. Acceptance Telemetry and Feedback Loop

> **Architecture context:** See Architecture Document, Layer 2. **Developer Guide context:** Developers report issues via Developer Guide, Section 11.

### Capture points

| Event | Captured | Storage |
|---|---|---|
| `blueprint_start` called | Task ID + spec hash + MCP request ID | `telemetry.blueprint_started` |
| `blueprint_result` retrieved | Full blueprint + pipeline duration + completion status | `telemetry.blueprint_completed` |
| Developer edits blueprint | Git diff | `telemetry.blueprint_edited` |
| `assemble_blueprint` called | Final blueprint + validated selections | `telemetry.blueprint_accepted` |
| `/accelerator.generate` runs | Generated files + skill versions | `telemetry.code_generated` |
| CI/CD result | Pass/fail + stage + error | `telemetry.cicd_results` |

### Weekly feedback loop

1. Review 10 lowest-acceptance-rate blueprints
2. Root cause: system prompt gap / catalog gap / tool metadata gap
3. Fix the relevant artifact
4. Add case to regression suite
5. Deploy fix to MCP Server, verify regression suite passes

---

## 4. Catalog Quality Engineering

> **Architecture context:** See Architecture Document, Layer 2 (Vertex AI Search data stores). **Developer Guide context:** Developer Guide, Section 4 (signal words that help the Solution Accelerator).

### Required metadata

**Patterns:** name, description, applicability, composition_rules, tags, archetype, status

**Skills:** name, use_when, do_not_use_when, required_tools (if applicable), version

**Tools:** name, connection_type (mcp_server/a2a_agent_card/function_tool), endpoint (if applicable), capabilities, workload_type

### Validation

```bash
python3 scripts/validate_catalog.py \
  --data-store sdlc-accelerators-patterns \
  --required-fields name,description,applicability,composition_rules,tags,archetype,status \
  --output reports/catalog_health_$(date +%Y%m%d).json
```

Run nightly. Alert on missing required fields. Block ingestion of invalid entries.

### Embedding freshness

Re-ingest on: document content change (automatic via CI), Vertex AI Search model upgrade (quarterly), or embedding regression detected.

---

## 4a. Catalog Backup and Disaster Recovery

> **Architecture context:** The Solution Accelerator's intelligence depends on three Vertex AI Search data stores (patterns, skills, tools). Its async task lifecycle depends on the AlloyDB Task Store. If the Vertex AI Search data stores are corrupted or deleted, the platform is non-functional. If the Task Store is unavailable, in-flight blueprint tasks fail (but are recoverable by re-running). This section covers backup, restore, and failover for both.

### Source of truth

All catalog content is version-controlled in GitHub:

| Catalog | GitHub repo | Format |
|---|---|---|
| Pattern Catalog | `github.com/[company]/sdlc-accelerators-patterns` | Markdown + YAML frontmatter per pattern |
| Skill Catalog | `github.com/[company]/sdlc-accelerators-skills` | SKILL.md files with frontmatter |
| Tool Registry | `github.com/[company]/sdlc-accelerators-tools` | YAML manifests per tool |

The GitHub repos are the source of truth. Vertex AI Search data stores are derived indexes — they can always be rebuilt from the repos.

### Backup strategy

| Component | Backup method | Frequency | Retention |
|---|---|---|---|
| Catalog source documents | GitHub repo (version-controlled) | Every commit | Indefinite (git history) |
| Vertex AI Search index metadata | Automated export to GCS bucket | Nightly | 30 days |
| Solution Accelerator system prompt | GitHub repo (version-controlled) | Every change | Indefinite |
| Regression test golden suite | GitHub repo | Every change | Indefinite |

### Restore procedure

**Scenario: Vertex AI Search data store corrupted or deleted**

1. Verify the GitHub source repos are intact (they are the source of truth)
2. Create new Vertex AI Search data stores with the same schema
3. Run the ingestion pipeline: `python3 scripts/ingest_catalog.py --source github --target [new-data-store-id]`
4. Run the enrichment validation pipeline to verify all required metadata fields
5. Run the search quality regression suite to verify recommendation quality
6. Update the Solution Accelerator API layer and pipeline job configurations to point to the new data stores
7. Deploy both components via the standard deployment procedure (Section 9)

**Estimated RTO:** 2–4 hours (ingestion ~1 hour, validation ~30 minutes, regression suite ~30 minutes, deployment ~1 hour)

**Scenario: Solution Accelerator system prompt corrupted**

1. Roll back to previous version in GitHub
2. Redeploy the pipeline job with the restored prompt (Section 9 deployment procedure)
3. Estimated RTO: 30 minutes

### Failover during recovery

While data stores are being rebuilt, the Solution Accelerator API layer can operate in **degraded mode**:
- `blueprint_start` creates a task, but the pipeline returns a cached response for specs matching a known golden test case (hash match)
- For unknown specs, returns an error with guidance: "Solution Accelerator temporarily unavailable. You can author the blueprint manually using the template in the Developer Guide (Section 5)."
- `validate_composition` and `assemble_blueprint` continue to work normally (they don't depend on Vertex AI Search)

### Task Store (AlloyDB) disaster recovery

The AlloyDB Task Store holds transient async task records (taskId, status, stage, progress, result) with a 24-hour TTL. It is **not** a durable data store — all content is derived from the spec/plan inputs and the pipeline output, both of which can be regenerated by re-running `/accelerator.blueprint`.

**Why AlloyDB Task Store DR is lower-priority than Vertex AI Search DR:**
- AlloyDB is a managed, highly available service with a 99.99% SLA and automated cross-region replication (compared to Vertex AI Search which requires manual index rebuilds)
- Task records are ephemeral (24h TTL) — no historical data is at risk
- Loss of in-flight tasks is recoverable: the developer simply re-runs `/accelerator.blueprint`

**Scenario: AlloyDB regional outage**
1. AlloyDB with cross-region replication fails over automatically to the read replica — no manual action required
2. If using single-region AlloyDB: the API layer returns errors on all `blueprint_start` / `blueprint_status` / `blueprint_result` calls
3. Recovery: wait for AlloyDB to restore (GCP manages automated failover), or promote the cross-region read replica and update API layer connection string
4. Notify developers via `#sdlc-accelerators` Slack: "Solution Accelerator temporarily unavailable due to AlloyDB outage. You can author blueprint manually (Developer Guide, Section 5) or wait for recovery."
5. Estimated RTO: 0 (cross-region replica auto-promotion) or 15–30 minutes (single-region, manual failover)

**Scenario: Task records corrupted or deleted**
1. No restore needed — task records are transient and self-healing via TTL
2. Any developer with a task in `working` state will see `blueprint_status` return an error or `not_found`
3. Developer re-runs `/accelerator.blueprint` — the pipeline generates a fresh result
4. No data loss — the spec/plan inputs are in the developer's workspace, not in AlloyDB

**Backup strategy:**
| Component | Backup method | Frequency | Retention |
|---|---|---|---|
| AlloyDB Task Store | **No backup required** — transient records with 24h TTL | N/A | N/A |
| AlloyDB Task Store schema/indexes | Documented in `github.com/[company]/sdlc-accelerators-infra` | Every change | Indefinite (git) |

---

## 5. Tool Lifecycle Management

> **Architecture context:** Architecture Document, Layer 2 (Tool Registry). **Developer Guide context:** Developer Guide, Section 11 (reporting missing tools).

### Tool states

| State | Effect on Solution Accelerator |
|---|---|
| `active` | Included normally |
| `deprecated` | Included with warning + alternative |
| `retired` | Excluded |
| `maintenance` | Excluded; auto-restored |

### Deprecation: set `deprecated` → warning for 90 days → set `retired`. Notify affected teams 30 days before retirement.

---

## 6. Production Failure Modes

> **Architecture context:** Architecture Document, Layer 2 (MCP Server). **Developer Guide context:** Developer Guide, Section 14 (Troubleshooting).

| Failure | Detection | Resolution |
|---|---|---|
| API layer unreachable | MCP health check (60s) | Cloud Run health, container status, OAuth token, VPC-SC |
| Pipeline stuck (tasks in `working` > 2h) | Nightly cleanup job | Mark as `failed` with timeout reason; investigate Cloud Run Jobs logs |
| Task Store unavailable | AlloyDB health check (60s) | AlloyDB has automated cross-region failover; verify instance status; if global outage, engage GCP support |
| Vertex AI Search down | Search endpoint health (60s) | Retry w/ backoff. If > 5 min: alert, serve cached results |
| Pipeline OOM | Cloud Run Jobs metrics | Increase memory. Review spec size. |
| Cloud Tasks queue jammed | Queue depth monitor | Flush via `gcloud tasks queues purge` (see §9, Cloud Tasks queue configuration). Mark orphaned AlloyDB task records as failed. |
| Stale embeddings | Regression suite (weekly) | Re-ingest. Run regression. |
| Skill version mismatch | Skill version check | Update preset.yml. Notify developers (Dev Guide, Section 1). |
| Tool endpoint down | Health check (5 min) | Set `maintenance`. Exclude from results. |
| System prompt regression | Telemetry (acceptance rate drop) | Roll back prompt. Add regression test. |
| Model quota exceeded | Gemini API monitoring | Request quota increase. Pipeline queues naturally. |
| Governance Guardian unreachable | MCP health check (60s) | Check Cloud Run health for Governance Guardian service. Same OAuth as Solution Accelerator. |
| `/accelerator.generate` blocked by governance gate | Critical or High findings remain in the latest assessment | `verify_generation_gate` reads `findings.md` from GCS via its AlloyDB pointer and returns `stop` if any Critical/High finding remains. Developer must resolve them, run `/accelerator.refresh` (re-sync `.md`↔`.drawio`), and re-run `/accelerator.assess`. When only Medium/Low remain, the gate writes one tech-debt JSON per finding to the GCS tech-debt bucket and returns `resume`. Check the GCS findings bucket and the AlloyDB pointer row (keyed by task_id, owner_id) if the gate cannot locate findings. |
| `/accelerator.assess` fails at PDF stage | Blueprint → PDF conversion error (missing/corrupt PNG, or findings PDF unparseable) | `assess_start` converts `app-blueprint.md` → PDF (sections + embedded PNGs) for the Eraser MCP server; `assess_result` converts the returned findings PDF → Markdown (Critical/High/Medium/Low). If a referenced PNG is missing, the section renders a placeholder and assessment proceeds. If the Eraser findings PDF can't be parsed, check the Eraser MCP server output format; the converter tolerates findings tables and labelled prose. |
| Governance assessment stuck | Assessment health check (3 min) | Check Cloud Tasks `governance-assess` queue. Flush if jammed. EA assessment engine may be down — contact EA office. |
| Tech Debt Registry unavailable | AlloyDB health (60s) | Same database as Solution Accelerator Task Store. Check connection pool. |
| `blueprint_result` returns 'artifacts not found' | Blueprint artifact store pointer missing in AlloyDB, or GCS objects unavailable | `blueprint_result` reads artifacts from GCS via the AlloyDB pointer (keyed by task_id, owner_id). Check the AlloyDB pointer row exists for the task_id and that the GCS prefix `blueprints/<owner>/<task>/` contains app-blueprint.md/.json + diagrams. Pointer is written at the end of `blueprint_start`; if that failed, re-run. |
| `app-blueprint.json` out of sync with `.md` or `.drawio.xml` | `/accelerator.generate` hash check detects mismatch, or `/accelerator.refresh` reports Case A/B/C | `/accelerator.refresh` performs bidirectional sync: if only .md changed (Case A), regenerates .drawio.xml + .json; if only .drawio changed (Case B), updates .md §2 narrative + .json; if both changed (Case C), reconciles differences with conflict detection. If sync fails, check: Eraser MCP server health (for .drawio/.png rendering), Solution Accelerator MCP Server health (for LLM-assisted .md updates), AlloyDB connection, and `.md` parse errors (malformed section headers). `/accelerator.assess` auto-triggers refresh; `/accelerator.generate` BLOCKS and requires explicit refresh. |
| `app-blueprint.json` corrupted or missing | `/accelerator.generate` fails to parse `.json` | Delete `app-blueprint.json` from workspace. Run `assemble_blueprint` manually (via coding agent MCP call) to regenerate from `.md`. The `.md` is always the source of truth — `.json` can always be regenerated. |
| `app-blueprint.json` edited directly by developer | Hash mismatch on next `/accelerator.generate` | Auto-resolved: `/accelerator.generate` detects `.md` hash differs from stored hash, regenerates `.json` from `.md` (overwriting manual edits). Warn developer: **never edit `.json` directly** — edits will be overwritten. |

### Escalation

| Severity | Response | Who |
|---|---|---|
| P1 — API layer down or all pipelines failing | 15 min | Platform Engineering on-call |
| P1 — Governance Guardian down (blocks all /accelerator.generate) | 15 min | Platform Engineering on-call + EA office |
| P2 — Degraded results or pipeline slow | 4 hours | Platform Engineering |
| P3 — Single tool/skill issue | 1 business day | Platform Engineering |
| P4 — Enhancement | Sprint planning | EA + Platform Engineering |

---

## 7. Pattern Composition Validator

> **Architecture context:** `validate_composition` MCP tool (Architecture Document, Layer 2). **Developer Guide context:** Developer Guide, Section 6 (iterating on design).

### Adjacency matrix

| Parent | Allowed Children | Forbidden |
|---|---|---|
| Coordinator | Sequential, Parallel, Loop, HITL, Custom | Another Coordinator |
| Sequential | Any except Coordinator | — |
| Parallel | Sequential, Loop, Custom, FunctionTool | LoopAgent |
| Loop | Sequential, Parallel, Custom, FunctionTool | Another Loop |
| HITL | FunctionTool, Custom | Parallel |

On failure: MCP Server returns `{"valid": false, "errors": [...]}` with reason + suggestion. Developer edits blueprint and retries.

---

## 8. EvalOps Operations

> **Architecture context:** Architecture Document, Layer 4 (3-layer EvalOps). **Developer Guide context:** Developer Guide, Section 4b (EvalOps workflow) and Section 7 (writing tests).

### Pre-commit hook

Runs 5–10 evalsets in <60s. If slow: check evalset count, SDK version, baseline_scores.json.

### Phoenix

Local: `localhost:6006`, 7-day retention. Deployed: OTel → Dynatrace, 30-day retention.

**Tracing scope:** Phoenix traces **generated agents at runtime** — LLM calls, tool calls, agent delegation within deployed agents. The Solution Accelerator background pipeline is **not** traced by Phoenix; it is traced via Cloud Logging (structured logs per pipeline stage) and Dynatrace APM (OTel spans for RAG query latency and LLM reasoning time). Platform engineers troubleshooting Solution Accelerator pipeline performance use Dynatrace dashboards (see §9, Health checks), not Phoenix.

### Harness 3-phase maintenance

Phase A (Arize gates): update thresholds quarterly. Phase B (AutoSxS): refresh baseline on golden dataset update. Phase C (HITL): expand reviewer pool if queue > 20.

### Golden dataset lifecycle

Starts as first-draft entries from acceptance criteria (see Developer Guide, Section 4a). Developer curates (Section 7). Production feedback weekly via Arize drift detection. Meta-evaluation quarterly: 50 AutoSxS samples → 3 reviewers → ≥85% agreement.

---

## 9. Solution Accelerator MCP Server Operations

> **Architecture context:** Architecture Document, Layer 2 (MCP Server with 5 tools, async via MCP Tasks). **Developer Guide context:** Developer Guide, Section 2.5 (how the blueprint is created asynchronously). **Blueprint template:** `app-blueprint-md-template-and-fnol-example.md` (12-section template structure and FNOL reference example).

The Solution Accelerator has two deployment components: the **MCP API layer** (Cloud Run Service) handling the three fast tools plus two deterministic tools, and the **background pipeline** (Cloud Run Jobs) running the LlmAgent work. A **AlloyDB Task Store** connects them.

### Health checks

| Check | Method | Frequency |
|---|---|---|
| API layer reachable | MCP protocol handshake | 60s |
| `blueprint_start` functional | Golden FNOL spec → task created | 3 min |
| Pipeline completion | Golden FNOL spec (1 integration, lightweight) → poll until completed | 3 min |
| `validate_composition` | Known-valid tree | 5 min |
| `assemble_blueprint` | Known selections | 5 min |
| Task Store | AlloyDB `SELECT 1` connection check | 60s |
| Cross-user access blocked | `blueprint_result` with wrong owner_id → 403 | 15 min |
| Eraser MCP server reachable | MCP health check to the Eraser MCP server | 5 min |
| Diagram rendering | Golden FNOL → verify `.drawio.xml` + `.png` all generated | 4 hours |

The pipeline completion check uses a lightweight golden spec (1 integration) that completes in <30 seconds, so a 3-minute interval adds negligible load while ensuring pipeline failures are detected within 3 minutes rather than 15.

**Eraser MCP server failure mode:** If the Eraser MCP server is unreachable, `/accelerator.refresh` has degraded behavior depending on the sync case:
- **Case A (.md changed → regenerate diagram):** BLOCKED — cannot generate new .drawio.xml from topology. The .md edits are preserved but the diagram is stale. Developer sees: "Eraser MCP server unavailable — diagram regeneration deferred. .json regenerated from .md but .drawio.xml is stale."
- **Case B (.drawio changed → update .md):** PARTIALLY DEGRADED — the LLM can still update .md §2 narrative from parsed .drawio.xml, and .json is regenerated. But .png cannot be re-rendered. Developer sees: ".md and .json updated. .png rendering deferred until the Eraser MCP server recovers."
- **Case C (both changed):** Same degradation as Case A for diagram regeneration.
- **In all cases:** The `.drawio.xml` source files are still valid and editable in the Draw.io VSCode extension (local, no cloud dependency). `.png` rendering will resume when the Eraser MCP server recovers. The `.md` and `.json` are updated to the extent possible without it.

### Versioning

The Solution Accelerator uses semantic versioning (`major.minor.patch`):
- **Major:** Breaking change to blueprint schema, MCP tool interface, or task lifecycle
- **Minor:** System prompt update, new pattern added, catalog change
- **Patch:** Bug fix, performance improvement

Maintain **2 versions in production** at all times (current + previous) for rollback.

### Authentication troubleshooting (OAuth 2.1 / Entra ID)

Both Solution Accelerator and Governance Guardian use OAuth 2.1 with Microsoft Entra ID. Same app registration, same audience scope (`sdlc-accelerators.mcp`), same JWKS endpoint. Tool access additionally requires membership in the **Solution Architect** Entra AD group (checked against the JWT `groups` claim on every call). See Architecture Document, Layer 2 Security for the full sequence diagram.

| Symptom | Cause | Resolution |
|---|---|---|
| 401 Unauthorized on first call | Token expired or never acquired | Developer: close and reopen VSCode to trigger fresh SSO login |
| 401 after long idle | Refresh token expired (>24 hours) | Developer: re-authenticate via browser SSO |
| 401 for one developer, others OK | Entra ID account issue | Check Entra ID: account active and not locked. For tool-access (403) issues, verify group membership includes the **Solution Architect** group. |
| 403 Forbidden | Token valid but wrong audience scope | Check Entra ID app registration: audience must be `sdlc-accelerators.mcp` |
| 403 Forbidden (insufficient_scope, group) | Token valid but developer not in Solution Architect group | Add the developer's Entra ID account to the **Solution Architect** AD group (object id configured as `SOLUTION_ARCHITECT_GROUP_ID` on both MCP Servers). No server restart needed — the next token will carry the updated `groups` claim. Verify the app registration emits the `groups` claim (optional claims / token configuration). |
| JWKS validation failure | Entra ID JWKS endpoint unreachable | Check network: MCP Server must reach `login.microsoftonline.com`. Check VPC-SC egress rules. |
| Intermittent 401 | JWKS cache stale after Entra ID key rotation | MCP Server JWKS cache TTL is 24 hours. Force refresh: restart Cloud Run revision. |

**Health check:** Entra ID JWKS endpoint reachability — `curl https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys` — 60-second frequency. Version metadata is embedded in every generated blueprint:

```yaml
# Generated by: solution-accelerator/v2.3.1
# System prompt: v1.8 (SHA: abc123)
```

When a developer reports an issue, the version metadata tells you exactly which prompt, catalog, and code produced the recommendation.

### Deployment

1. Build containers: API layer image + pipeline job image
2. Run full regression suite against staging (including async round-trip: start → poll → result)
3. **Drain in-flight tasks:** Check AlloyDB for tasks in `working` state. Wait up to 5 minutes for in-flight tasks to complete on the current pipeline revision. If tasks don't complete within 5 minutes, they will finish on the old Cloud Run Jobs revision (Cloud Run Jobs retains the old revision until all executions complete).
   ```bash
   # Check in-flight tasks
   psql $ALLOYDB_CONNECTION -c "SELECT task_id, status, created_at FROM blueprint_tasks WHERE status = 'working';"
   # If empty, proceed. If not, wait or proceed knowing old revision will handle them.
   ```
4. Deploy API layer with `--no-traffic`
5. Deploy pipeline job revision
6. Smoke test: golden FNOL → `blueprint_start` → poll → `blueprint_result` → verify blueprint
7. Traffic shift (API layer): 10% (15 min) → 50% (15 min) → 100%
8. Monitor telemetry 24 hours — roll back if acceptance drops > 5%
9. Verify no tasks remain on old pipeline revision after 1 hour. If old executions persist, investigate.

### System prompt updates

1. Draft new prompt
2. Full regression suite against new prompt (run via pipeline staging)
3. Compare: pattern accuracy, tool accuracy, confidence distribution
4. Deploy pipeline job with updated prompt via standard procedure
5. Monitor telemetry 1 week

### Scaling

| Concern | Setting |
|---|---|
| API layer concurrent connections | Cloud Run Service `--max-instances` (lightweight, high concurrency) |
| Pipeline concurrent jobs | Cloud Run Jobs `--max-concurrent` (adjust when > 10 simultaneous) |
| Cloud Tasks queue depth | Monitor queue depth; alert if > 50 pending tasks |
| Large specs (OOM in pipeline) | Cloud Run Jobs `--memory` |
| Slow reasoning in pipeline | Cloud Run Jobs `--cpu` |
| Cold start avoidance (API layer) | Cloud Run Service `--min-instances 1` |
| Task Store capacity | AlloyDB Autopilot auto-scales; monitor row count via `pg_stat_user_tables` |

### Cloud Tasks queue configuration

The `blueprint-tasks` queue connects `blueprint_start` (API layer) to the background pipeline (Cloud Run Jobs).

| Setting | Value | Rationale |
|---|---|---|
| Queue name | `blueprint-tasks` | Single queue for all blueprint pipeline tasks |
| Max dispatches per second | 10 | Matches Cloud Run Jobs max-concurrent |
| Max concurrent dispatches | 10 | Prevents pipeline overload |
| Max retry attempts | 3 | Failed tasks retry with exponential backoff |
| Min backoff | 10 seconds | Allow transient failures to resolve |
| Max backoff | 300 seconds | Cap retry delay at 5 minutes |
| Dead-letter topic | `blueprint-tasks-dlq` (Pub/Sub) | Tasks that fail after 3 retries land here for investigation |

**IAM permissions:**
- API layer service account: `cloudtasks.tasks.create` on `blueprint-tasks`
- Pipeline job service account: invoked by Cloud Tasks push handler (no explicit queue permission needed)
- Platform engineering admin: `cloudtasks.queues.purge` for emergency flush

**Flushing stuck tasks:**
```bash
# View queue state
gcloud tasks queues describe blueprint-tasks --project=$PROJECT

# Purge all pending tasks (emergency only — cancels all queued blueprints)
gcloud tasks queues purge blueprint-tasks --project=$PROJECT

# After purge, mark corresponding AlloyDB task records as "failed"
python3 scripts/mark_orphaned_tasks.py --status=failed --reason="queue_purged"
```

### Task Store maintenance

| Concern | Procedure |
|---|---|
| TTL enforcement | Scheduled Cloud Scheduler job runs hourly: `DELETE FROM blueprint_tasks WHERE created_at < NOW() - INTERVAL '24 hours'` |
| Orphaned tasks (stuck in `working` > 2 hours) | Nightly cleanup job marks as `failed` with reason "timeout" |
| Storage growth | Monitor row count; at > 10K concurrent records, investigate high-retry developers |

---

## 10. Governance Guardian MCP Server Operations

> **Architecture context:** Governance Guardian Architecture Extension (full design). **Developer Guide context:** Developer Guide, Section 2.7a (`/accelerator.assess`), Section 2.8 (governance gate in `/accelerator.generate`).

The Governance Guardian uses the same async MCP Tasks pattern as the Solution Accelerator. It shares the same AlloyDB instance (separate table `governance_tasks`) and the same OAuth 2.1 / Entra ID authentication (same `sdlc-accelerators.mcp` audience scope — no separate Entra ID app registration needed). See §9 Authentication troubleshooting for common auth issues. See Architecture Document, Layer 2 Security for the full OAuth 2.1 sequence diagram.

### Health checks

| Check | Method | Frequency |
|---|---|---|
| API layer reachable | MCP protocol handshake | 60s |
| `assess_start` functional | Golden FNOL solution package → task created | 3 min |
| Assessment completion | Golden FNOL solution package → poll until completed | 3 min |
| `recordTechDebt` functional | Known assessment ID → resume/stop signal | 5 min |
| `getAssessmentHistory` functional | Known solution_id → returns assessment history | 5 min |
| EA assessment engine reachable | Health endpoint on EA service | 60s |
| Task Store (`governance_tasks`) | AlloyDB `SELECT 1` | 60s |
| Tech Debt Registry (`tech_debt`) | AlloyDB `SELECT 1` | 60s |

### Deployment

The Governance Guardian follows the same deployment procedure as the Solution Accelerator (§9): build → regression suite → drain → canary → full deploy. The EA assessment engine is deployed independently by the EA office — it is a black box to SDLC Accelerators.

### Cloud Tasks queue

| Setting | Value |
|---|---|
| Queue name | `governance-assess` |
| Max dispatches/sec | 10 |
| Max concurrent | 10 |
| Max retries | 3 |
| Dead-letter topic | `governance-assess-dlq` |

### Task Store maintenance

Same as Solution Accelerator (§9): hourly cleanup of `governance_tasks` records older than 24 hours. The `tech_debt` table is **NOT** subject to TTL cleanup — tech debt records are persistent until manually resolved.

### EA assessment engine SLA

The EA assessment engine is a black box. Platform Engineering monitors the transport (is it reachable?) but does not operate the assessment logic. SLA is negotiated between Platform Engineering and the EA office:

| Metric | Target | Alert |
|---|---|---|
| Assessment completion p95 | < 60 seconds | > 120 seconds |
| Assessment availability | 99.5% | < 99% |
| False positive rate (showstoppers that shouldn't be) | < 5% | > 10% |

### 10a. Governance Guardian MCP Wire Format

**`assess_start` — request:**
```json
{
  "method": "tools/call",
  "params": {
    "name": "assess_start",
    "arguments": {
      "solution_package": { "solution_id": "...", "tsa_component_diagram": {...}, "nfrs": {...}, "..." : "..." }
    }
  }
}
```

**`assess_start` — response:**
```json
{ "content": [{ "type": "text", "text": "{\"taskId\": \"gov-456\", \"status\": \"accepted\", \"pollInterval\": 10000}" }] }
```

**`assess_status` — response (stage values):**
```json
{ "content": [{ "type": "text", "text": "{\"taskId\": \"gov-456\", \"status\": \"working\", \"stage\": \"checking_patterns\", \"message\": \"Evaluating pattern adherence...\"}" }] }
```

Stage values: `accepted` → `extracting_artifacts` → `checking_compliance` → `checking_patterns` → `scoring_nfrs` → `scoring_hadr` → `scoring_security` → `compiling_scorecard` → `completed` (or `failed`).

**`assess_result` — response (completed):**
```json
{ "content": [{ "type": "text", "text": "{\"assessment_id\": \"GA-2026-0089\", \"overall_score\": 88, \"grade\": \"B\", \"scorecard\": {...}, \"findings\": [...], \"verdict\": \"PASSED\"}" }] }
```

**`recordTechDebt` — response (resume):**
```json
{ "content": [{ "type": "text", "text": "{\"signal\": \"resume\", \"tech_debt_id\": \"TD-2026-0142\", \"debt_items\": [{\"finding_id\": \"F-002\", \"severity\": \"high\", \"title\": \"WAF rules\"}]}" }] }
```

**`recordTechDebt` — response (stop):**
```json
{ "content": [{ "type": "text", "text": "{\"signal\": \"stop\", \"showstoppers\": [{\"finding_id\": \"F-001\", \"severity\": \"showstopper\", \"title\": \"No cross-region DR\"}]}" }] }
```

---

## 11. Apigee Proxy, Per-Agent Workload Identity, and API Hub A2A Operations

> **Architecture context:** Architecture Document, Layer 3 (Apigee proxy + Workload Identity + API Hub registration generation from app-blueprint.md) and Layer 5 (Runtime & Operate).

Apigee proxy routes, per-agent Workload Identity IAM bindings, and API Hub registration entries are generated by `/accelerator.generate` from `app-blueprint.md` and provisioned during CI/CD. The PRS Security pillar automatically validates Gateway routes, Agent Identity tokens, and Registry entries at build time (see Developer Guide §2 for developer-facing troubleshooting of proxy and identity issues). The health checks below monitor runtime state AFTER deployment.

### Apigee proxy routes

**What's generated:** One Apigee proxy per `tools.mcp_servers[]` entry (§5) with auth from `mcp_server_configs[]` (§7). One A2A proxy per `tools.a2a_agents[]` entry discovered via API Hub.

| Health check | Method | Frequency |
|---|---|---|
| Proxy routes match blueprint tool bindings | Compare Apigee proxy count vs tool_bindings[] count | Per deployment |
| MCP route connectivity | Synthetic request through each proxy → target MCP server health endpoint | 5 min |
| A2A route connectivity | Synthetic A2A handshake → target Agent Card URL | 5 min |

| Failure | Detection | Resolution |
|---|---|---|
| Apigee proxy missing for a tool binding | Deployment smoke test fails | Regenerate: re-run `/accelerator.generate`. Check blueprint §5 for missing binding. |
| MCP route timeout | Apigee health check fails | Check target MCP server. Check VPC-SC egress. Check mTLS cert expiry. |
| A2A target unreachable | Apigee health check fails | Query API Hub for target agent status. If `retired`, notify the target agent's team. |

### Per-agent Workload Identity

**What's generated:** One service account per agent in topology (§3). IAM bindings ONLY for tools assigned to that agent in §5.

| Health check | Method | Frequency |
|---|---|---|
| All agents have service accounts | Compare GCP IAM service accounts vs blueprint topology | Per deployment |
| No overprivileged agents | Verify no agent SA has `roles/owner` or `roles/editor` | Per deployment |
| IAM bindings match blueprint | Each SA's roles match its tool bindings | Per deployment |

| Failure | Detection | Resolution |
|---|---|---|
| Agent blocked from calling assigned tool | Developer reports tool call rejected (403) | Check IAM bindings: is the role granted for this SA? If missing, regenerate from blueprint. |
| Overprivileged agent found | Security audit | Remove excessive roles. Regenerate from blueprint to restore least-privilege. |

### API Hub A2A agent entries

**What's generated:** One API Hub entry (`type=a2a_agent`) per deployed agent, with capabilities, Agent Card URL, and lifecycle status.

| Health check | Method | Frequency |
|---|---|---|
| API Hub entry exists post-deployment | Query API Hub for agent name + version | Post-deployment |
| Agent Card URL accessible | HTTP GET to Agent Card URL → valid JSON | 5 min |
| Lifecycle status accurate | API Hub status matches Cloud Run health | 60s |

| Failure | Detection | Resolution |
|---|---|---|
| API Hub entry not created | Post-deployment check fails | Run the `apihub register` step manually from the CI/CD pipeline definition. |
| Stale entry (agent retired but still listed as active) | API Hub shows `active` but Cloud Run has no instances | Update API Hub lifecycle to `retired`. Run cleanup. |

**The flywheel:** Every agent deployed via SDLC Accelerators registers in API Hub. Future Solution Accelerator runs query API Hub via `search_a2a_agents()` and discover these agents for A2A delegation — reusing deployed agents instead of rebuilding. The more agents deployed, the richer the API Hub catalog, the more the Solution Accelerator can recommend A2A reuse.

---

## /accelerator.refresh — Operations Guide

The `/accelerator.refresh` command validates edited files and regenerates derived artifacts. It's also auto-triggered by `/accelerator.assess` and `/accelerator.generate` when stale files are detected.

### What /accelerator.refresh Does (Server-Side)

| Step | Action | Server resource used | Failure mode |
|---|---|---|---|
| 0. validate_spec | Check 6 signal categories (ordering words, data systems, partners, IF/THEN, sensitive data, acceptance criteria). PASS/WARN/BLOCK. | CPU only (regex + pattern matching) | BLOCK → pipeline aborts with specific guidance per signal. WARN → continues with risk flags. |
| 1. Validate Part I | Parse §1-§7, check completeness | CPU only (no external calls) | Missing section → WARN with guidance |
| 2. .md↔.drawio consistency | Parse .drawio.xml, extract agent nodes, compare with §5 | CPU only | Mismatch → report specific differences |
| 3. Sync Part II | Generate/update §8-§12 rows from Part I changes | API Hub (for MCP configs), company standards API | API Hub timeout → use cached defaults |
| 4. Regenerate .json | Parse all 12 sections → emit JSON | CPU only | Parse error → report line number |
| 5. Regenerate .png | Eraser MCP server render (DSL → .png, synchronous) | Eraser MCP server | Render timeout → keep existing .png, warn |

### Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| "blueprint_start returned BLOCK — validate_spec failed" | Spec missing critical signals | Check the specific BLOCK signal: §2 no ordering words → add "first/then/parallel". §4 vague systems → name specific tech. §7 prose rules → use IF/THEN. See Developer Guide "Writing Specs That Pass Signal Validation". |
| "/accelerator.refresh returns 'Section missing'" | Developer deleted a governance section (§1-§7) from Part I | Restore the section. All 7 governance sections are required. Part II sections (§8-§12) are auto-regenerated if deleted. |
| ".md↔.drawio mismatch won't resolve" | Developer edited .md AND .drawio with conflicting changes | Pick one source of truth: update §5 to match diagram, or update diagram to match §5. Then re-run refresh. |
| "Part II rows not updating for new agent" | API Hub lookup failed for the new agent's MCP server | Check API Hub connectivity. If the MCP server isn't registered in API Hub yet, manually add the §8 row with connection details. |
| ".json not regenerating" | Table parse error — malformed markdown table in .md | Check the .md tables for missing pipe characters, misaligned columns, or special characters. Fix and re-run. |
| ".png not regenerating" | Eraser MCP server unavailable | Check Eraser MCP server health. The .drawio.xml is still valid — .png will regenerate on next successful refresh. |
| "Auto-refresh slowing down /accelerator.assess" | Large .drawio files causing slow .png rendering | Pre-run `/accelerator.refresh` manually before `/accelerator.assess` so the auto-refresh is a no-op (files already current). |
| "Stale .json detected but auto-refresh fails" | .md has structural errors that block parsing | Run `/accelerator.refresh` manually for detailed error messages. Fix .md errors, then re-run `/accelerator.assess`. |

### Skip-Refresh Safety Mechanism

Both `/accelerator.assess` and `/accelerator.generate` auto-detect stale files before proceeding:

```
Staleness check (runs as Step 0 of /accelerator.assess and /accelerator.generate):
  1. Compare app-blueprint.md modified_time with app-blueprint.json modified_time
  2. Compare diagrams/*.drawio.xml modified_times with diagrams/*.png modified_times
  3. If ANY source file is newer than its derived file:
     → Auto-run refresh (validate + sync + regenerate)
     → If refresh succeeds: proceed with assessment/generation
     → If refresh fails: STOP with error, ask developer to fix and run /accelerator.refresh manually
```

This ensures the developer can NEVER accidentally assess or generate code from stale files — even if they forget to run `/accelerator.refresh` after editing.

## Spec Signal Validation — Troubleshooting

The Solution Accelerator validates specs before running the RAG pipeline. When developers report "my blueprint quality is low" or "the Solution Accelerator returned generic results," check the spec signal quality first.

| Symptom | Likely cause | Resolution |
|---|---|---|
| "blueprint_start returned immediately with an error" | BLOCK — one or more critical signals missing | Read the error message — it identifies the specific section and signal. Guide developer to add ordering words (§2), specific data systems (§4), or IF/THEN business rules (§7). |
| "Blueprint has wrong patterns" | §2 missing ordering words | Check §2: does it use "first", "then", "in parallel", "loop until"? Without these, pattern retrieval is random. |
| "Blueprint suggests MCP but should be A2A" | §5 missing "own system" flag | Check §5: does each external partner specify whether "they operate their own system"? Missing → defaults to MCP wrapping. |
| "FunctionTools are empty stubs" | §7 has prose instead of IF/THEN | Check §7: are rules in "IF condition THEN action" format? Prose rules can't be converted to code. |
| "No Model Armor callbacks generated" | §8 missing or empty | Check §8: are PII/PHI/financial classifications listed? If §4 has user-facing systems but §8 is empty, it's likely an oversight. |
| "EvalOps pipeline has no golden dataset entries" | §10 has unmeasurable criteria | Check §10: are criteria measurable? "Fast" → no. "< 5 min" → yes. Each measurable criterion becomes a golden dataset entry. |
| "spec_quality_score is < 60" | Multiple WARN signals | Review the validation output — each WARN includes a specific recommendation. Fix warnings for better blueprint quality. |

---

## /accelerator.refresh — Operational Procedures

### Health Checks

| Check | Method | Expected |
|---|---|---|
| `refresh` tool available | Call refresh with empty .md | Returns validation error (not connection error) |
| Eraser MCP server rendering | Render test DSL | Returns .drawio.xml + .png (synchronous) |
| Staleness detection | Modify .md, call assess | Auto-refresh triggers before assessment |

### Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| "/accelerator.refresh returns connection error" | Solution Accelerator MCP Server unreachable | Check MCP Server health. Refresh uses the same server as blueprint_start. |
| ".json not regenerated after refresh" | .md has unparseable tables | Check refresh validation report — it identifies which table failed to parse. Fix table markdown syntax. |
| ".png not regenerated after refresh" | Eraser MCP server render failed | Check the Eraser MCP server logs for rendering errors. Verify the DSL/.drawio.xml is valid. |
| "Part II sections have wrong defaults for new agent" | API Hub lookup failed for new tool | Check API Hub connectivity. If API Hub is down, refresh uses fallback defaults (30s timeout, 3x retry). Developer can override in §8. |
| "/accelerator.assess says 'Auto-refreshing' every time" | Developer never runs /accelerator.refresh | Normal behavior — assess auto-detects stale .json. No action needed, but running refresh explicitly is faster. |
| "/accelerator.generate blocked with 'stale .json'" | Developer edited .md but didn't refresh or assess | Run /accelerator.refresh (or /accelerator.assess which auto-refreshes). Then re-run /accelerator.generate. |
| "Part II overrides were lost after refresh" | Bug — refresh should preserve overrides | Check if the developer edited §5 (Part I) in a way that changed the agent that had overrides. If the agent_id changed, Part II can't match the override to the old row. |
| ".md↔.drawio consistency warning but both are correct" | Diagram has labels that don't exactly match §5 agent_id | Ensure agent node labels in .drawio exactly match agent_id values in §5 topology table. Case-sensitive. |

### Staleness Detection — How It Works

Every refresh writes `.accelerator-hashes` to the workspace:
```json
{
  "blueprint_md_hash": "sha256:...",
  "blueprint_json_source_md_hash": "sha256:...",
  "drawio_hashes": { "component-architecture.drawio.xml": "sha256:..." },
  "png_source_drawio_hashes": { "component-architecture.png": "sha256:..." },
  "last_refresh": "2026-05-28T14:30:00Z"
}
```

- `/accelerator.assess` compares current .md hash with `blueprint_json_source_md_hash`. If different → auto-refresh.
- `/accelerator.generate` does the same check but BLOCKS instead of auto-refreshing.
- Hashes are SHA-256 of file content. Whitespace-only changes still trigger staleness (intentional — any edit should be validated).

---

*This runbook is maintained by the Platform Engineering team. Review cadence: Monthly.*

*For architectural decisions, see the SDLC Accelerators Architecture Document. For developer workflows, see the SDLC Accelerators Developer Guide. For governance assessment design, see the Governance Guardian Architecture Extension.*
