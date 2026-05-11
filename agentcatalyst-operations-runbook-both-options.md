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
| 1. Wire-Level API Calls | Layer 2 — Blueprint Advisor MCP Server | Section 5 — Understanding the YAML Blueprint |
| 2. Search Quality Regression | Layer 2 — Blueprint Advisor | Section 8 — Reading Confidence Scores |
| 3. Acceptance Telemetry | Layer 2 — Blueprint Advisor | Section 9 — When the Blueprint Advisor Gets It Wrong |
| 4. Catalog Quality | Layer 2 — Vertex AI Search data stores | Section 4 — Writing Effective Specs |
| 5. Tool Lifecycle | Layer 2 — Tool Registry | Section 11 — Reporting Issues |
| 6. Failure Modes | Layer 2 — Blueprint Advisor MCP Server | Section 14 — Troubleshooting |
| 7. Composition Validator | Layer 2 — Pattern composition | Section 6 — Iterating on the Design |
| 8. EvalOps Operations | Layer 4 — EvalOps 3-layer lifecycle | Section 4b — EvalOps Workflow |
| 9. MCP Server Operations | Layer 2 — Blueprint Advisor MCP Server | Section 5 — Understanding the YAML Blueprint |

---

## 1. Wire-Level Vertex AI Search API Calls

> **Architecture context:** The Blueprint Advisor MCP Server (see Architecture Document, Layer 2) exposes three MCP tools to the coding agent: `recommend_architecture` (advisory), `validate_composition` (deterministic), and `assemble_blueprint` (deterministic). Internally, `recommend_architecture` invokes the Blueprint Advisor LlmAgent, which uses three RAG tools to query Vertex AI Search. These RAG tools are NOT exposed to the coding agent.

### Transport security

All communication between the coding agent and the Blueprint Advisor MCP Server is encrypted:

| Hop | Protocol | Encryption |
|---|---|---|
| Coding agent → Cloud Run | MCP over HTTPS | TLS 1.3 (Cloud Run default) |
| Cloud Run → Vertex AI Search | gRPC | TLS 1.3 (Google internal) |
| Cloud Run → Gemini API | HTTPS | TLS 1.3 (Google internal) |

**Spec content in transit:** The developer's `spec.md` and `plan.md` are transmitted as MCP tool call parameters over TLS-encrypted connections. Content is processed in-memory on the Blueprint Advisor server and is NOT persisted to disk or logged. Only the spec hash (SHA-256) is captured in telemetry for traceability.

**Data residency:** The Blueprint Advisor MCP Server runs in a specific GCP region (configured at deployment). Spec content does not leave this region. Vertex AI Search data stores are co-located in the same region.

**Audit trail:** Every `recommend_architecture` call logs: timestamp, authenticated user identity, spec hash, plan hash, MCP request ID, response size, latency. Content is NOT logged. See Section 3 (Acceptance Telemetry) for the full telemetry schema.

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
| Latency (p50) | 200–400ms | > 800ms |
| Latency (p99) | 600–1,200ms | > 2,000ms |
| Results per query | 3–5 | < 1 |
| Cost per query | ~$0.003 | N/A |
| Full `recommend_architecture` (3 RAG + LLM) | 15–30 seconds | > 60 seconds |

### Troubleshooting

| Symptom | Cause | Resolution |
|---|---|---|
| Empty results | Data store not indexed / embedding stale | Re-run ingestion pipeline, verify document count |
| Irrelevant results | Missing/incorrect metadata | Check `metadata.archetype` and `metadata.tags` |
| High latency | Large corpus + complex query | Add `filter`, reduce `pageSize` |
| Permission denied | Missing `discoveryengine.viewer` role | Grant IAM role |
| MCP Server error to coding agent | LlmAgent failure | Check Cloud Run logs — common: OOM, quota exceeded |

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
  "business_rules": { "severity_classifier_has_rules": true, "rule_count_minimum": 3 }
}
```

The `business_rules` assertions verify that business rules pass through from spec to YAML. When the Blueprint Advisor drops rules, the coding agent generates stubs instead of first-draft implementations — a significant quality regression.

### Execution

```bash
python3 scripts/run_regression.py \
  --golden-dir tests/golden/ \
  --mcp-endpoint mcp://blueprint-advisor.[company-domain].run.app \
  --output results/$(date +%Y%m%d).json
```

The suite calls the MCP Server via the same protocol the coding agent uses — testing the exact code path developers experience.

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
| `recommend_architecture` called | Full YAML + spec hash + MCP request ID | `telemetry.blueprint_generated` |
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

> **Architecture context:** The Blueprint Advisor's intelligence depends entirely on three Vertex AI Search data stores. If these are corrupted or deleted, the platform is non-functional. This section covers backup, restore, and failover.

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
6. Update the Blueprint Advisor MCP Server configuration to point to the new data stores
7. Deploy the updated MCP Server via the standard deployment procedure (Section 9)

**Estimated RTO:** 2–4 hours (ingestion ~1 hour, validation ~30 minutes, regression suite ~30 minutes, deployment ~1 hour)

**Scenario: Blueprint Advisor system prompt corrupted**

1. Roll back to previous version in GitHub
2. Redeploy the MCP Server with the restored prompt (Section 9 deployment procedure)
3. Estimated RTO: 30 minutes

### Failover during recovery

While data stores are being rebuilt, the Blueprint Advisor MCP Server can operate in **degraded mode**:
- `recommend_architecture` returns a cached response for specs matching a known golden test case (hash match)
- For unknown specs, returns an error with guidance: "Blueprint Advisor temporarily unavailable. You can author the YAML manually using the template in the Developer Guide (Section 5)."
- `validate_composition` and `assemble_blueprint` continue to work normally (they don't depend on Vertex AI Search)

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
| MCP Server unreachable | MCP health check (60s) | Cloud Run health, container status, OAuth token, VPC-SC |
| Vertex AI Search down | Search endpoint health (60s) | Retry w/ backoff. If > 5 min: alert, serve cached results |
| Blueprint Advisor OOM | Cloud Run metrics | Increase memory. Review spec size. |
| Stale embeddings | Regression suite (weekly) | Re-ingest. Run regression. |
| Skill version mismatch | Skill version check | Update preset.yml. Notify developers (Dev Guide, Section 1). |
| Tool endpoint down | Health check (5 min) | Set `maintenance`. Exclude from results. |
| System prompt regression | Telemetry (acceptance rate drop) | Roll back prompt. Add regression test. |
| Model quota exceeded | Gemini API monitoring | Request quota increase. Implement queuing. |

### Escalation

| Severity | Response | Who |
|---|---|---|
| P1 — MCP Server down | 15 min | Platform Engineering on-call |
| P2 — Degraded results | 4 hours | Platform Engineering |
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

### Harness 3-phase maintenance

Phase A (Arize gates): update thresholds quarterly. Phase B (AutoSxS): refresh baseline on golden dataset update. Phase C (HITL): expand reviewer pool if queue > 20.

### Golden dataset lifecycle

Starts as first-draft entries from acceptance criteria (see Developer Guide, Section 4a). Developer curates (Section 7). Production feedback weekly via Arize drift detection. Meta-evaluation quarterly: 50 AutoSxS samples → 3 reviewers → ≥85% agreement.

---

## 9. Blueprint Advisor MCP Server Operations

> **Architecture context:** Architecture Document, Layer 2 (MCP Server with 3 tools). **Developer Guide context:** Developer Guide, Section 5 (how the YAML is created).

### Health checks

| Check | Method | Frequency |
|---|---|---|
| MCP reachable | Protocol handshake | 60s |
| `recommend_architecture` | Golden FNOL spec | 5 min |
| `validate_composition` | Known-valid tree | 5 min |
| `assemble_blueprint` | Known selections | 5 min |

### Versioning

The Blueprint Advisor uses semantic versioning (`major.minor.patch`):
- **Major:** Breaking change to YAML schema or MCP tool interface
- **Minor:** System prompt update, new pattern added, catalog change
- **Patch:** Bug fix, performance improvement

Maintain **2 versions in production** at all times (current + previous) for rollback. Version metadata is embedded in every generated YAML:

```yaml
# Generated by: blueprint-advisor/v2.3.1
# System prompt: v1.8 (SHA: abc123)
```

When a developer reports an issue, the version metadata tells you exactly which prompt, catalog, and code produced the recommendation.

### Deployment

1. Build container with updated LlmAgent / system prompt
2. Run full regression suite against staging
3. Deploy with `--no-traffic`
4. Smoke test: golden FNOL → `recommend_architecture` → verify
5. Traffic shift: 10% (15 min) → 50% (15 min) → 100%
6. Monitor telemetry 24 hours — roll back if acceptance drops > 5%

### System prompt updates

1. Draft new prompt
2. Full regression suite against new prompt
3. Compare: pattern accuracy, tool accuracy, confidence distribution
4. Deploy via standard procedure
5. Monitor telemetry 1 week

### Scaling

| Concern | Cloud Run setting |
|---|---|
| Concurrent calls | `--max-instances` (adjust when > 10 simultaneous) |
| Large specs (OOM) | `--memory` |
| Slow reasoning | `--cpu` |
| Cold start avoidance | `--min-instances 1` |

---

*This runbook is maintained by the Platform Engineering team. Review cadence: Monthly.*

*For architectural decisions, see the AgentCatalyst Architecture Document. For developer workflows, see the AgentCatalyst Developer Guide.*
