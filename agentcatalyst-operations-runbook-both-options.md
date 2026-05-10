# AgentCatalyst Operations Runbook

*Operational procedures, monitoring, and maintenance for the AgentCatalyst platform. This is a living document maintained by the Platform Engineering team.*

*Applies to: Both GA and agents-cli architecture variants. All procedures in this runbook are platform-level — the Blueprint Advisor, Vertex AI Search catalogs, telemetry pipelines, and quality engineering processes are identical across variants. Runtime-specific operations (Cloud Run scaling for GA, agents-cli command restrictions for agents-cli) are covered in the respective architecture documents.*

*Companion to: agentcatalyst-architecture.md (GA) and agentcatalyst-agentscli-architecture.md*

---

## 1. Wire-Level Vertex AI Search API Calls

The Blueprint Advisor's three FunctionTools (`search_patterns`, `search_skills`, `search_tools`) each invoke the Vertex AI Search REST API. Understanding the wire-level interaction matters for performance tuning, cost analysis, and troubleshooting.

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

### Response processing

The Blueprint Advisor processes the response in this order:
1. Read `results[].document.structData` for structured metadata (name, applicability, composition rules)
2. Read `results[].document.derivedStructData.snippets` for contextual descriptions
3. Read `summary.summaryText` for the search engine's natural language synthesis
4. Apply confidence scoring: exact metadata match = high, snippet match = medium, summary-only = low

### Data store identifiers

| FunctionTool | Data Store ID | Contents |
|---|---|---|
| `search_patterns` | `agentcatalyst-patterns` | 11 agentic patterns with 8 sections each |
| `search_skills` | `agentcatalyst-skills` | Reusable skills with use_when/do_not_use_when frontmatter |
| `search_tools` | `agentcatalyst-tools` | MCP servers, A2A Agent Cards, FunctionTool definitions |

### Performance characteristics

| Metric | Typical value | Alert threshold |
|---|---|---|
| Latency (p50) | 200-400ms | > 800ms |
| Latency (p99) | 600-1200ms | > 2000ms |
| Results per query | 3-5 | < 1 (empty results) |
| Cost per query | ~$0.003 | N/A |
| Blueprint Advisor total (3 queries) | ~$0.01 | N/A |

### Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| Empty results for valid queries | Data store not indexed / embedding stale | Re-run ingestion pipeline, verify document count |
| Irrelevant results | Missing or incorrect metadata frontmatter | Check `metadata.archetype` and `metadata.tags` on source documents |
| High latency | Large document corpus + complex query | Add `filter` to narrow scope, reduce `pageSize` |
| "Permission denied" | Service account missing `discoveryengine.viewer` role | Grant IAM role on the data store |

---

## 2. Search Quality Regression Suite

The Blueprint Advisor's behavior depends on three artifacts that change over time: the system prompt, the pattern catalog, and the tool registry. Any change to any artifact can degrade search quality without anyone noticing.

### Golden test suite structure

Maintain 30–50 reference specs with known-good YAML outputs (golden YAMLs). Each test case comprises:

```
tests/
├── golden/
│   ├── fnol-basic/
│   │   ├── spec.md          ← Input spec
│   │   ├── plan.md          ← Input plan
│   │   ├── expected.yaml    ← Golden YAML output
│   │   └── assertions.json  ← Specific fields to validate
│   ├── fnol-brownfield/
│   │   ├── spec.md
│   │   ├── plan.md
│   │   ├── expected.yaml
│   │   └── assertions.json
│   └── microservice-order-mgmt/
│       ├── ...
```

### Assertions format

```json
{
  "pattern_selection": {
    "root_pattern": "coordinator",
    "must_contain": ["sequential", "parallel"],
    "must_not_contain": ["loop_inside_parallel"]
  },
  "tool_assignment": {
    "bigquery_assigned_to": "enrichment_agent",
    "cloud_sql_assigned_to": "fnol_coordinator"
  },
  "skill_discovery": {
    "must_discover": ["adk-agents"],
    "min_confidence": "medium"
  }
}
```

### Regression test execution

Run the suite on every change to:
- Blueprint Advisor system prompt
- Pattern catalog (new pattern, updated metadata)
- Tool registry (new tool, changed endpoint)
- Vertex AI Search configuration (re-indexing, schema change)

```bash
# Run regression suite
python3 scripts/run_regression.py \
  --golden-dir tests/golden/ \
  --blueprint-advisor-url https://blueprint-advisor.run.app \
  --output results/$(date +%Y%m%d).json

# Check results
python3 scripts/check_assertions.py results/$(date +%Y%m%d).json
```

### Quality metrics

| Metric | Target | Alert threshold |
|---|---|---|
| Pattern selection accuracy | ≥ 90% of golden cases | < 85% |
| Tool assignment accuracy | ≥ 85% of golden cases | < 80% |
| Skill discovery recall | ≥ 90% | < 85% |
| Zero-result queries | 0% of golden cases | > 0% |
| Regression from previous run | 0 new failures | > 0 |

### Cadence

| Trigger | Action |
|---|---|
| System prompt change | Full suite (30-50 cases) |
| Pattern catalog change | Pattern-related cases only |
| Tool registry change | Tool-related cases only |
| Weekly (automated) | Full suite |
| Pre-release | Full suite + manual review of any failures |

---

## 3. Acceptance Telemetry and Feedback Loop

Generated YAMLs are observed in two ways: what the Blueprint Advisor produced and what the developer kept after review. The diff between the two is the highest-value signal in the entire platform.

### Telemetry capture points

| Event | What's captured | Where it's stored |
|---|---|---|
| Blueprint generated | Full YAML + spec.md hash + plan.md hash + query-response pairs from Vertex AI Search | BigQuery `telemetry.blueprint_generated` |
| Blueprint edited | Git diff of developer's edits to the YAML | BigQuery `telemetry.blueprint_edited` |
| Blueprint accepted | Final YAML committed to repo (post-edit) | BigQuery `telemetry.blueprint_accepted` |
| Code generated | List of generated files + skill versions used | BigQuery `telemetry.code_generated` |
| CI/CD result | Pass/fail + which stage failed + error details | BigQuery `telemetry.cicd_results` |

### Dashboard views

**Blueprint Advisor accuracy dashboard** (Looker):
- Acceptance rate: % of generated YAMLs accepted without edits
- Most-edited fields: which YAML fields developers change most often (signals Blueprint Advisor weakness)
- Pattern selection accuracy: % of cases where generated pattern matches final pattern
- Tool assignment accuracy: % of tool-to-agent assignments kept unchanged

**Trend dashboard**:
- Acceptance rate over time (should increase as system prompt improves)
- Edit heatmap by YAML section (highlights systematic weaknesses)
- Query-to-result relevance scores over time

### Feedback loop process

1. **Weekly review**: Platform team reviews the 10 lowest-acceptance-rate blueprints
2. **Root cause**: Classify each as system prompt gap, catalog gap, or tool metadata gap
3. **Fix**: Update the relevant artifact (prompt, catalog entry, or tool frontmatter)
4. **Validate**: Add the case to the regression suite as a new golden test
5. **Deploy**: Push the fix and verify regression suite passes

### Meta-evaluation (quarterly)

Sample 50 AutoSxS decisions from the EvalOps pipeline. Route to 3 human reviewers. Measure agreement between AutoSxS and human judgment. If agreement drops below 85%, recalibrate AutoSxS thresholds.

---

## 4. Catalog Quality Engineering

The Blueprint Advisor's correctness depends entirely on the quality of the metadata in Vertex AI Search. Search returns noisy results when enrichment is incomplete.

### Required metadata per catalog entry

**Pattern Catalog entries:**

| Field | Required? | Example |
|---|---|---|
| `name` | Yes | `coordinator-pattern` |
| `description` | Yes | "Root orchestration pattern for multi-agent systems" |
| `applicability` | Yes | "Use when the workflow requires multiple specialized agents coordinated by a central agent" |
| `composition_rules` | Yes | "Can contain: Sequential, Parallel, Loop, HITL. Cannot contain: another Coordinator." |
| `tags` | Yes | `["multi-agent", "orchestration", "root-pattern"]` |
| `archetype` | Yes | `agentic` |
| `status` | Yes | `production` |

**Skill Catalog entries:**

| Field | Required? | Example |
|---|---|---|
| `name` | Yes | `adk-agents` |
| `use_when` | Yes | "Building ADK agent classes with correct imports and constructors" |
| `do_not_use_when` | Yes | "Building non-agentic applications (microservices, pipelines)" |
| `required_tools` | If applicable | `["vertex-ai-search", "cloud-run"]` |
| `version` | Yes | `1.2.0` |

**Tool Registry entries:**

| Field | Required? | Example |
|---|---|---|
| `name` | Yes | `claims-database` |
| `connection_type` | Yes | `mcp_server` or `a2a_agent_card` or `function_tool` |
| `endpoint` | If MCP/A2A | `https://claims-mcp.internal:8443` |
| `capabilities` | Yes | "Query active insurance claims by policy number, date range, or claimant" |
| `workload_type` | Yes | `transactional` |
| `data_domain` | Yes | `claims` |
| `sla` | Recommended | `p99 < 500ms` |

### Enrichment validation pipeline

Run nightly against all catalog entries:

```bash
python3 scripts/validate_catalog.py \
  --data-store agentcatalyst-patterns \
  --required-fields name,description,applicability,composition_rules,tags,archetype,status \
  --output reports/catalog_health_$(date +%Y%m%d).json
```

Alert if any entry is missing required fields. Block ingestion of new entries that fail validation.

### Embedding freshness

Vertex AI Search embeddings are generated at ingestion time. If the underlying document changes, re-ingest to update the embedding. Stale embeddings cause semantic drift — the search query matches the old version of the document, not the current one.

**Re-ingestion triggers:**
- Document content updated (automatic via CI pipeline)
- Vertex AI Search model upgrade (manual, scheduled quarterly)
- Embedding quality regression detected in search quality suite

---

## 5. Tool Lifecycle Management

Tools and tasks in the registry are not permanent. APIs change. Servers are decommissioned. Partners sunset endpoints.

### Tool states

| State | Meaning | Effect on Blueprint Advisor |
|---|---|---|
| `active` | Available for use | Included in search results normally |
| `deprecated` | Still works but being replaced | Included in results with warning; alternative suggested |
| `retired` | No longer available | Excluded from search results |
| `maintenance` | Temporarily unavailable | Excluded from results; auto-restored after maintenance window |

### Deprecation process

1. Set tool status to `deprecated` with `deprecated_date` and `replacement` fields
2. Blueprint Advisor includes deprecated tools in results but appends: "⚠️ This tool is deprecated. Use {replacement} instead."
3. After 90 days, set status to `retired`
4. Retired tools are excluded from search results but retained in the registry for audit trail

### Partner endpoint changes

When a partner changes their API endpoint:
1. Update the tool's `endpoint` field in the registry
2. Update the tool's `capabilities` if the API contract changed
3. Re-run tool-related regression tests
4. Notify teams with active blueprints that reference the tool

### Decommissioning checklist

- [ ] Identify all active blueprints referencing the tool
- [ ] Notify affected teams (30-day notice)
- [ ] Set status to `deprecated` with replacement recommendation
- [ ] Update regression suite to use replacement tool
- [ ] After 90 days, set status to `retired`
- [ ] Archive tool documentation (do not delete)

---

## 6. Production Failure Modes

| Failure | Impact | Detection | Resolution |
|---|---|---|---|
| Vertex AI Search unavailable | Blueprint Advisor returns errors | Health check on `/search` endpoint (every 60s) | Retry with exponential backoff. If sustained > 5 min, alert platform team. Blueprint Advisor returns cached results for known specs. |
| Blueprint Advisor OOM | Generation fails for large specs | Cloud Run memory metrics in Dynatrace | Increase Cloud Run memory limit. Review spec size — may need chunking for very large specs. |
| Stale embeddings | Incorrect pattern/skill/tool recommendations | Search quality regression suite (weekly) | Re-ingest affected documents. Run regression suite to verify. |
| Skill version mismatch | Generated code uses wrong API patterns | Skill version check in preset.yml | Update skill version in preset. Notify developers to re-install preset. |
| Tool endpoint down | Generated code references unreachable endpoint | Health check on tool endpoints (every 5 min) | Set tool status to `maintenance`. Blueprint Advisor excludes from results. Restore when endpoint recovers. |
| System prompt regression | Blueprint Advisor makes poor recommendations | Acceptance telemetry (acceptance rate drop) | Roll back system prompt to previous version. Investigate root cause. Add regression test. |
| Catalog poisoning | Malicious or incorrect metadata ingested | Ingestion validation pipeline + human review | Remove affected entries. Re-run regression suite. Tighten ingestion validation rules. |

### Escalation matrix

| Severity | Response time | Who |
|---|---|---|
| P1 — Blueprint Advisor down | 15 minutes | Platform Engineering on-call |
| P2 — Degraded results (acceptance rate < 70%) | 4 hours | Platform Engineering |
| P3 — Single tool/skill issue | 1 business day | Platform Engineering |
| P4 — Enhancement request | Sprint planning | EA + Platform Engineering |

---

## 7. Pattern Composition Validator

The Blueprint Advisor validates pattern compositions before including them in the YAML. Invalid compositions are caught before the developer sees them.

### Adjacency matrix

The validator uses a static adjacency matrix defining which patterns can nest inside which:

| Parent Pattern | Allowed Children | Forbidden Children |
|---|---|---|
| Coordinator | Sequential, Parallel, Loop, HITL, Custom | Another Coordinator |
| Sequential | Any except Coordinator | — |
| Parallel | Sequential, Loop, Custom, FunctionTool | LoopAgent (infinite loop risk) |
| Loop | Sequential, Parallel, Custom, FunctionTool | Another Loop (nested loops) |
| HITL | FunctionTool, Custom | Parallel (can't parallelize human review) |

### Validation rules

```python
def validate_composition(blueprint_yaml):
    errors = []
    for agent in blueprint_yaml['agents']:
        parent = agent['pattern']
        for child in agent.get('sub_agents', []):
            child_pattern = child['pattern']
            if child_pattern in FORBIDDEN_CHILDREN[parent]:
                errors.append({
                    'agent': agent['name'],
                    'parent_pattern': parent,
                    'child_pattern': child_pattern,
                    'reason': f"{child_pattern} cannot nest inside {parent}",
                    'suggestion': ALTERNATIVES.get((parent, child_pattern), "Restructure the agent hierarchy")
                })
    return errors
```

### What happens when validation fails

1. Blueprint Advisor flags the composition in the YAML with a `⚠️ COMPOSITION WARNING` comment
2. Suggests an alternative composition
3. Developer can override the warning (the YAML is human-editable)
4. If developer keeps the invalid composition, acceptance telemetry captures it for review

---

## 8. EvalOps Operations

### Pre-commit hook maintenance

The pre-commit inner loop evaluator (`tests/eval_inner_loop.py`) runs 5-10 evalsets in under 60 seconds. If it starts taking longer:
- Check evalset count (may have grown beyond 10)
- Check Vertex AI Evaluation SDK version (upgrade may improve performance)
- Check baseline_scores.json (may need recalibration after model upgrade)

### Arize Phoenix operations

Phoenix runs at `localhost:6006` during local development. In deployed environments, traces export to OTel Collector → Dynatrace.
- **Trace retention**: 30 days in Dynatrace, 7 days in Phoenix local
- **Storage**: ~50MB per 1000 agent invocations
- **Cleanup**: automated nightly purge of traces older than retention period

### Harness 3-phase pipeline maintenance

- **Phase A (Arize quality gates)**: Update thresholds quarterly based on production baseline
- **Phase B (AutoSxS)**: Refresh golden dataset baseline when golden dataset is updated
- **Phase C (HITL triage)**: Monitor queue depth — if > 20 items, expand reviewer pool

### Golden dataset lifecycle operations

| Stage | Frequency | Who | Action |
|---|---|---|---|
| Starter dataset generation | Per use case | Automated (from spec acceptance criteria) | Verify generated entries match spec intent |
| Developer curation | During development | Developer | Add edge cases, correct expected outputs |
| Production feedback | Weekly (automated) | Arize drift detection | Sample 10 failures, route to annotation queue |
| Human annotation | Weekly | Domain experts | Label sampled failures, update golden dataset |
| Meta-evaluation | Quarterly | Platform team | Audit AutoSxS decisions against human judgment (≥85% agreement) |

---

*This runbook is maintained by the Platform Engineering team. Last updated: [Date]. Review cadence: Monthly.*
