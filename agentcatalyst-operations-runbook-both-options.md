# AgentCatalyst — Operations Runbook

**Operational procedures, monitoring, and maintenance for the AgentCatalyst platform**
*This is a living document maintained by the Platform Engineering team.*

*Applies to: Both GA and agents-cli architecture variants. All procedures in this runbook are platform-level — the Blueprint Advisor MCP Server, Vertex AI Search catalogs, telemetry pipelines, and quality engineering processes are identical across variants. Runtime-specific operations (Cloud Run scaling for GA, agents-cli FORBIDDEN command enforcement for agents-cli) are covered in the respective architecture documents.*

### Related Documents

| Document | Audience | Relationship to this runbook |
|---|---|---|
| **AgentCatalyst Architecture Document** (GA or agents-cli) | Architects | Provides the WHY behind each system this runbook maintains. When you need to understand why the Blueprint Advisor MCP Server is designed a certain way, consult the Architecture Document (Layer 2). |
| **AgentCatalyst Developer Guide** (GA or agents-cli) | Developers | Provides the HOW for developers. When a developer reports an issue, this runbook tells you how to diagnose it. The Developer Guide (Section 9 and Section 11) tells developers what information to include in tickets. |

### Cross-reference map

| This runbook section | Architecture doc section | Developer guide section |
|---|---|---|
| 1. Wire-Level API Calls | Layer 2 — Blueprint Advisor MCP Server | Section 2.5 — `/catalyst.blueprint` (async invocation) + Section 5 — Understanding the YAML Blueprint |
| 2. Search Quality Regression | Layer 2 — Blueprint Advisor | Section 8 — Reading Confidence Scores |
| 3. Acceptance Telemetry | Layer 2 — Blueprint Advisor | Section 9 — When the Blueprint Advisor Gets It Wrong |
| 4. Catalog Quality | Layer 2 — Vertex AI Search data stores | Section 4 — Writing Effective Specs |
| 5. Tool Lifecycle | Layer 2 — Tool Registry | Section 11 — Reporting Issues |
| 6. Failure Modes | Layer 2 — Blueprint Advisor MCP Server | Section 14 — Troubleshooting |
| 7. Composition Validator | Layer 2 — Pattern composition | Section 6 — Iterating on the Design |
| 8. EvalOps Operations | Layer 4 — EvalOps 3-layer lifecycle | Section 4b — EvalOps Workflow |
| 9. MCP Server Operations | Layer 2 — Blueprint Advisor MCP Server | Section 2.5 — `/catalyst.blueprint` (async invocation) |

---

## 1. Wire-Level Vertex AI Search API Calls

> **Architecture context:** The Blueprint Advisor MCP Server (see Architecture Document, Layer 2) exposes five MCP tools to the coding agent: `blueprint_start` (async start), `blueprint_status` (poll), `blueprint_result` (retrieve), `validate_composition` (deterministic), and `assemble_blueprint` (deterministic). The first three implement the MCP Tasks async pattern — `blueprint_start` creates a background task that runs the Blueprint Advisor LlmAgent, the coding agent polls `blueprint_status` for progress, and retrieves the result via `blueprint_result`. Internally, the background pipeline uses three RAG tools to query Vertex AI Search. These RAG tools are NOT exposed to the coding agent.

### Transport security

All communication between the coding agent and the Blueprint Advisor MCP Server is encrypted:

| Hop | Protocol | Encryption |
|---|---|---|
| Coding agent → Cloud Run API layer | MCP over HTTPS | TLS 1.3 (Cloud Run default) |
| Cloud Run API layer → AlloyDB Task Store | PostgreSQL wire protocol | TLS 1.3 (AlloyDB enforced) |
| Cloud Run Jobs (pipeline) → Vertex AI Search | gRPC | TLS 1.3 (Google internal) |
| Cloud Run Jobs (pipeline) → Gemini API | HTTPS | TLS 1.3 (Google internal) |

**Spec content in transit:** The developer's `spec.md` and `plan.md` are transmitted as `blueprint_start` parameters over TLS-encrypted connections. Content is stored in the AlloyDB Task Store (encrypted at rest) during pipeline processing and auto-deleted after the 24-hour TTL. Content is NOT logged. Only the spec hash (SHA-256) is captured in telemetry for traceability.

**Data residency:** The Blueprint Advisor API layer and background pipeline run in a specific GCP region (configured at deployment). Spec content does not leave this region. Vertex AI Search data stores and the AlloyDB Task Store are co-located in the same region.

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

> **Developer Guide context:** Developers see confidence scores in the YAML blueprint (Developer Guide, Section 8). When they report low-confidence results, check the response processing chain above.

### Data store identifiers

| RAG Tool (internal) | Data Store ID | Contents |
|---|---|---|
| `search_patterns()` | `agentcatalyst-patterns` | 11 agentic patterns (8 sections each) |
| `search_skills()` | `agentcatalyst-skills` | Reusable skills with use_when/do_not_use_when |
| `search_tools()` | `agentcatalyst-tools` | MCP servers, A2A Agent Cards, FunctionTool defs |

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
    "text": "{\"taskId\": \"a1b2c3d4...\", \"status\": \"completed\", \"yaml\": \"<app-blueprint.yaml content>\", \"confidence_scores\": {...}}"
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

The `business_rules` assertions verify that business rules pass through from spec to YAML. When the Blueprint Advisor drops rules, the coding agent generates stubs instead of first-draft implementations — a significant quality regression.

The `async_lifecycle` assertions verify the MCP Tasks transport layer — not just the content quality. If the async handoff breaks (e.g., Cloud Tasks enqueue fails silently, AlloyDB writes are delayed, status transitions skip stages), these assertions catch it before developers experience the failure. A **deliberately malformed spec** golden test case should also be included to verify that the pipeline produces a `failed` task with a structured error rather than hanging indefinitely.

### Execution

```bash
python3 scripts/run_regression.py \
  --golden-dir tests/golden/ \
  --mcp-endpoint mcp://blueprint-advisor.[company-domain].run.app \
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
| `blueprint_result` retrieved | Full YAML + pipeline duration + completion status | `telemetry.blueprint_completed` |
| Developer edits YAML | Git diff | `telemetry.blueprint_edited` |
| `assemble_blueprint` called | Final YAML + validated selections | `telemetry.blueprint_accepted` |
| `/catalyst.generate` runs | Generated files + skill versions | `telemetry.code_generated` |
| CI/CD result | Pass/fail + stage + error | `telemetry.cicd_results` |

### Weekly feedback loop

1. Review 10 lowest-acceptance-rate blueprints
2. Root cause: system prompt gap / catalog gap / tool metadata gap
3. Fix the relevant artifact
4. Add case to regression suite
5. Deploy fix to MCP Server, verify regression suite passes

---

## 4. Catalog Quality Engineering

> **Architecture context:** See Architecture Document, Layer 2 (Vertex AI Search data stores). **Developer Guide context:** Developer Guide, Section 4 (signal words that help the Blueprint Advisor).

### Required metadata

**Patterns:** name, description, applicability, composition_rules, tags, archetype, status

**Skills:** name, use_when, do_not_use_when, required_tools (if applicable), version

**Tools:** name, connection_type (mcp_server/a2a_agent_card/function_tool), endpoint (if applicable), capabilities, workload_type

### Validation

```bash
python3 scripts/validate_catalog.py \
  --data-store agentcatalyst-patterns \
  --required-fields name,description,applicability,composition_rules,tags,archetype,status \
  --output reports/catalog_health_$(date +%Y%m%d).json
```

Run nightly. Alert on missing required fields. Block ingestion of invalid entries.

### Embedding freshness

Re-ingest on: document content change (automatic via CI), Vertex AI Search model upgrade (quarterly), or embedding regression detected.

---

## 4a. Catalog Backup and Disaster Recovery

> **Architecture context:** The Blueprint Advisor's intelligence depends on three Vertex AI Search data stores (patterns, skills, tools). Its async task lifecycle depends on the AlloyDB Task Store. If the Vertex AI Search data stores are corrupted or deleted, the platform is non-functional. If the Task Store is unavailable, in-flight blueprint tasks fail (but are recoverable by re-running). This section covers backup, restore, and failover for both.

### Source of truth

All catalog content is version-controlled in GitHub:

| Catalog | GitHub repo | Format |
|---|---|---|
| Pattern Catalog | `github.com/[company]/agentcatalyst-patterns` | Markdown + YAML frontmatter per pattern |
| Skill Catalog | `github.com/[company]/agentcatalyst-skills` | SKILL.md files with frontmatter |
| Tool Registry | `github.com/[company]/agentcatalyst-tools` | YAML manifests per tool |

The GitHub repos are the source of truth. Vertex AI Search data stores are derived indexes — they can always be rebuilt from the repos.

### Backup strategy

| Component | Backup method | Frequency | Retention |
|---|---|---|---|
| Catalog source documents | GitHub repo (version-controlled) | Every commit | Indefinite (git history) |
| Vertex AI Search index metadata | Automated export to GCS bucket | Nightly | 30 days |
| Blueprint Advisor system prompt | GitHub repo (version-controlled) | Every change | Indefinite |
| Regression test golden suite | GitHub repo | Every change | Indefinite |

### Restore procedure

**Scenario: Vertex AI Search data store corrupted or deleted**

1. Verify the GitHub source repos are intact (they are the source of truth)
2. Create new Vertex AI Search data stores with the same schema
3. Run the ingestion pipeline: `python3 scripts/ingest_catalog.py --source github --target [new-data-store-id]`
4. Run the enrichment validation pipeline to verify all required metadata fields
5. Run the search quality regression suite to verify recommendation quality
6. Update the Blueprint Advisor API layer and pipeline job configurations to point to the new data stores
7. Deploy both components via the standard deployment procedure (Section 9)

**Estimated RTO:** 2–4 hours (ingestion ~1 hour, validation ~30 minutes, regression suite ~30 minutes, deployment ~1 hour)

**Scenario: Blueprint Advisor system prompt corrupted**

1. Roll back to previous version in GitHub
2. Redeploy the pipeline job with the restored prompt (Section 9 deployment procedure)
3. Estimated RTO: 30 minutes

### Failover during recovery

While data stores are being rebuilt, the Blueprint Advisor API layer can operate in **degraded mode**:
- `blueprint_start` creates a task, but the pipeline returns a cached response for specs matching a known golden test case (hash match)
- For unknown specs, returns an error with guidance: "Blueprint Advisor temporarily unavailable. You can author the YAML manually using the template in the Developer Guide (Section 5)."
- `validate_composition` and `assemble_blueprint` continue to work normally (they don't depend on Vertex AI Search)

### Task Store (AlloyDB) disaster recovery

The AlloyDB Task Store holds transient async task records (taskId, status, stage, progress, result) with a 24-hour TTL. It is **not** a durable data store — all content is derived from the spec/plan inputs and the pipeline output, both of which can be regenerated by re-running `/catalyst.blueprint`.

**Why AlloyDB Task Store DR is lower-priority than Vertex AI Search DR:**
- AlloyDB is a managed, highly available service with a 99.99% SLA and automated cross-region replication (compared to Vertex AI Search which requires manual index rebuilds)
- Task records are ephemeral (24h TTL) — no historical data is at risk
- Loss of in-flight tasks is recoverable: the developer simply re-runs `/catalyst.blueprint`

**Scenario: AlloyDB regional outage**
1. AlloyDB with cross-region replication fails over automatically to the read replica — no manual action required
2. If using single-region AlloyDB: the API layer returns errors on all `blueprint_start` / `blueprint_status` / `blueprint_result` calls
3. Recovery: wait for AlloyDB to restore (GCP manages automated failover), or promote the cross-region read replica and update API layer connection string
4. Notify developers via `#agentcatalyst` Slack: "Blueprint Advisor temporarily unavailable due to AlloyDB outage. You can author YAML manually (Developer Guide, Section 5) or wait for recovery."
5. Estimated RTO: 0 (cross-region replica auto-promotion) or 15–30 minutes (single-region, manual failover)

**Scenario: Task records corrupted or deleted**
1. No restore needed — task records are transient and self-healing via TTL
2. Any developer with a task in `working` state will see `blueprint_status` return an error or `not_found`
3. Developer re-runs `/catalyst.blueprint` — the pipeline generates a fresh result
4. No data loss — the spec/plan inputs are in the developer's workspace, not in AlloyDB

**Backup strategy:**
| Component | Backup method | Frequency | Retention |
|---|---|---|---|
| AlloyDB Task Store | **No backup required** — transient records with 24h TTL | N/A | N/A |
| AlloyDB Task Store schema/indexes | Documented in `github.com/[company]/agentcatalyst-infra` | Every change | Indefinite (git) |

---

## 5. Tool Lifecycle Management

> **Architecture context:** Architecture Document, Layer 2 (Tool Registry). **Developer Guide context:** Developer Guide, Section 11 (reporting missing tools).

### Tool states

| State | Effect on Blueprint Advisor |
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

### Escalation

| Severity | Response | Who |
|---|---|---|
| P1 — API layer down or all pipelines failing | 15 min | Platform Engineering on-call |
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

On failure: MCP Server returns `{"valid": false, "errors": [...]}` with reason + suggestion. Developer edits YAML and retries.

---

## 8. EvalOps Operations

> **Architecture context:** Architecture Document, Layer 4 (3-layer EvalOps). **Developer Guide context:** Developer Guide, Section 4b (EvalOps workflow) and Section 7 (writing tests).

### Pre-commit hook

Runs 5–10 evalsets in <60s. If slow: check evalset count, SDK version, baseline_scores.json.

### Phoenix

Local: `localhost:6006`, 7-day retention. Deployed: OTel → Dynatrace, 30-day retention.

**Tracing scope:** Phoenix traces **generated agents at runtime** — LLM calls, tool calls, agent delegation within deployed agents. The Blueprint Advisor background pipeline is **not** traced by Phoenix; it is traced via Cloud Logging (structured logs per pipeline stage) and Dynatrace APM (OTel spans for RAG query latency and LLM reasoning time). Platform engineers troubleshooting Blueprint Advisor pipeline performance use Dynatrace dashboards (see §9, Health checks), not Phoenix.

### Harness 3-phase maintenance

Phase A (Arize gates): update thresholds quarterly. Phase B (AutoSxS): refresh baseline on golden dataset update. Phase C (HITL): expand reviewer pool if queue > 20.

### Golden dataset lifecycle

Starts as first-draft entries from acceptance criteria (see Developer Guide, Section 4a). Developer curates (Section 7). Production feedback weekly via Arize drift detection. Meta-evaluation quarterly: 50 AutoSxS samples → 3 reviewers → ≥85% agreement.

---

## 9. Blueprint Advisor MCP Server Operations

> **Architecture context:** Architecture Document, Layer 2 (MCP Server with 5 tools, async via MCP Tasks). **Developer Guide context:** Developer Guide, Section 2.5 (how the YAML is created asynchronously).

The Blueprint Advisor has two deployment components: the **MCP API layer** (Cloud Run Service) handling the three fast tools plus two deterministic tools, and the **background pipeline** (Cloud Run Jobs) running the LlmAgent work. A **AlloyDB Task Store** connects them.

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

The pipeline completion check uses a lightweight golden spec (1 integration) that completes in <30 seconds, so a 3-minute interval adds negligible load while ensuring pipeline failures are detected within 3 minutes rather than 15.

### Versioning

The Blueprint Advisor uses semantic versioning (`major.minor.patch`):
- **Major:** Breaking change to YAML schema, MCP tool interface, or task lifecycle
- **Minor:** System prompt update, new pattern added, catalog change
- **Patch:** Bug fix, performance improvement

Maintain **2 versions in production** at all times (current + previous) for rollback. Version metadata is embedded in every generated YAML:

```yaml
# Generated by: blueprint-advisor/v2.3.1
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
6. Smoke test: golden FNOL → `blueprint_start` → poll → `blueprint_result` → verify YAML
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

*This runbook is maintained by the Platform Engineering team. Review cadence: Monthly.*

*For architectural decisions, see the AgentCatalyst Architecture Document. For developer workflows, see the AgentCatalyst Developer Guide.*
