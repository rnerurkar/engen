# app-blueprint.md — Template and FNOL Reference Example

## 1. Template Structure

The Blueprint Advisor produces `app-blueprint.md` — a structured markdown document that serves as:
- The **single source of truth** for architectural decisions (replacing the previous YAML format)
- The **input to Governance Guardian** (`/catalyst.assess` extracts all 7 artifact types directly from this file — no separate drawio, NFR, or ADL files needed)
- The **input to code generation** (`/catalyst.generate` reads this file deterministically)
- A **human-readable review artifact** that renders natively in GitHub and VSCode

### Why markdown over YAML

The previous `app-blueprint.yaml` required the Governance Guardian to extract artifacts from multiple workspace files (drawio XML, separate NFR documents, separate ADL files). The markdown format assembles everything into one document: component diagrams as inline PNG references, sequence diagrams as inline mermaid code, NFRs and ADL as tables, and tech stack as structured sections. The SA reviews one file, the Governance Guardian reads one file, and the code generator consumes one file.

### Workspace file layout

When `blueprint_result` delivers the blueprint, the coding agent writes the following files to the feature directory:

```
features/fnol-claims-agent/
├── app-blueprint.md                    ← The blueprint (markdown)
├── fnol-component-diagram.png          ← Component diagram (rendered PNG)
├── fnol-component-diagram.drawio.xml   ← Component diagram (editable drawio)
├── fnol-hadr-diagram.png               ← HA/DR views (rendered PNG)
├── fnol-hadr-diagram.drawio.xml        ← HA/DR views (editable drawio)
└── ... (spec.md, plan.md already here)
```

The `.md` file references the PNGs with relative paths (`![Component Diagram](fnol-component-diagram.png)`) so they render inline when viewed in VSCode or GitHub. The `.drawio.xml` files are for editing in draw.io — the SA can modify the architecture, then re-run `/catalyst.assess` with the updated diagrams.

### How the MCP Server delivers binary files

The `blueprint_result` MCP tool returns a JSON response with three fields:

```json
{
  "markdown": "<full content of app-blueprint.md>",
  "diagrams": [
    {
      "filename": "fnol-component-diagram.png",
      "format": "png",
      "content_base64": "<base64-encoded PNG bytes>"
    },
    {
      "filename": "fnol-component-diagram.drawio.xml",
      "format": "drawio",
      "content_base64": "<base64-encoded drawio XML>"
    },
    {
      "filename": "fnol-hadr-diagram.png",
      "format": "png",
      "content_base64": "<base64-encoded PNG bytes>"
    },
    {
      "filename": "fnol-hadr-diagram.drawio.xml",
      "format": "drawio",
      "content_base64": "<base64-encoded drawio XML>"
    }
  ],
  "spec_hash": "sha256:abc123...",
  "plan_hash": "sha256:def456...",
  "blueprint_hash": "sha256:ghi789..."
}
```

The `/catalyst.blueprint` prompt file instructs the coding agent to:
1. Write `app-blueprint.md` from the `markdown` field
2. For each entry in `diagrams`, base64-decode and write to the same directory
3. Verify the PNG filenames match the `![...]()` references in the markdown

### Diagram generation inside the Blueprint Advisor pipeline

The Blueprint Advisor's background pipeline (Stage 4: `assemble_blueprint`) generates diagrams as follows:

- **Component diagram (PNG + drawio):** The pipeline assembles a graphviz DOT description from the agent topology, MCP connections, A2A boundaries, and infrastructure components. It renders the DOT to PNG (via graphviz) and converts to drawio XML (via a DOT-to-drawio transform). Both are included in the `diagrams` array.
- **HA/DR diagram (PNG + drawio):** The pipeline reads the DR strategy from `plan.md` and generates lifecycle scenario views (Initial Provisioning → Component Failure / HA → DR Failover → DR Failback) as a graphviz diagram. Rendered to PNG and converted to drawio XML.
- **Sequence diagrams (mermaid):** Generated as mermaid `sequenceDiagram` code and embedded inline in the markdown. No separate file needed — mermaid renders natively in GitHub and VSCode.

---

## 2. Template Sections

> **Version note:** Section numbering is per app-blueprint.md template **v1.0**. If sections are added or reordered, update both this template document and the Governance Guardian extraction table in `governance-guardian-architecture.md`.

The `app-blueprint.md` template has 14 sections. Each section maps to a specific consumer:

| Section | Consumer | Format |
|---|---|---|
| 1. Metadata | All | Key-value table |
| 2. Pattern Composition | Code generator, Governance Guardian | Table + validation notes |
| 3. Agent Topology | Code generator, Governance Guardian | Table + inline mermaid component diagram |
| 4. Component Diagrams | SA review, Governance Guardian | Inline PNG reference + drawio XML reference |
| 5. Tool Bindings | Code generator, Governance Guardian | Table |
| 6. Skill References | Code generator | Table |
| 7. MCP Server Configs | Code generator | Table |
| 8. Infrastructure Modules | Code generator, Governance Guardian | Table |
| 9. Business Rules | Code generator | Structured text per FunctionTool |
| 10. NFRs | Governance Guardian | Table |
| 11. Architecture Decisions Log | Governance Guardian | Table |
| 12. Tech Stack | Governance Guardian | Table |
| 13. HA/DR Views | SA review, Governance Guardian | Inline PNG reference + drawio XML reference + lifecycle table |
| 14. Sequence Diagrams | SA review, Governance Guardian | Inline mermaid code |
| 15. Evaluation Config | Code generator | Table |
| 16. Screening Config | Code generator | Table |
| 17. Pipeline Configs | Code generator | Table |
| 18. Confidence Scores | SA review | Table |

### What `/catalyst.assess` reads from this file

The Governance Guardian extracts all 7 artifact types from `app-blueprint.md` directly:

| Artifact | Extracted from section |
|---|---|
| TSA component diagram | §4 (PNG reference → reads the PNG file from workspace) |
| HA/DR views | §13 (PNG reference → reads the PNG file; lifecycle table) |
| Sequence diagrams | §14 (inline mermaid code) |
| NFRs | §10 (table) |
| Architecture Decisions Log | §11 (table) |
| Tech stack | §12 (table) |
| Patterns used | §2 (table) |

Because everything is in one file (or referenced from it), the coding agent no longer needs to hunt for separate drawio files, NFR documents, or ADL directories. The `/catalyst.assess` prompt file simply reads `app-blueprint.md` and packages the content.

---

## 3. FNOL Reference Example

```markdown
# app-blueprint.md — FNOL Claims Agent

> Generated by Blueprint Advisor MCP Server
> Spec hash: sha256:a1b2c3d4e5f6...
> Plan hash: sha256:f6e5d4c3b2a1...
> Blueprint hash: sha256:7890abcdef12...
> Generated: 2026-05-20T14:30:00Z
> Confidence: 0.92 overall

---

## 1. Metadata

| Field | Value |
|---|---|
| Solution ID | fnol-claims-agent |
| Archetype | agentic |
| Preset | agentcatalyst-enterprise |
| Framework | Google ADK (Python) |
| Runtime | Cloud Run (GA) |
| Gateway | Apigee Runtime Gateway (GA) |
| Region (primary) | us-east1 |
| Region (DR) | us-west1 |
| DR Strategy | Pilot Light — Cold Standby |
| CI/CD | Jenkins + Harness |

> **Note:** This FNOL example uses Jenkins + Harness (enterprise overlay for this company). The GCP-native default is Cloud Build + Cloud Deploy. The `pipeline_configs` section (§17) adapts to whichever CI/CD overlay skill is active.

---

## 2. Pattern Composition

| Pattern | Role | Nesting | Confidence |
|---|---|---|---|
| SequentialAgent | Root orchestrator | — | 0.95 |
| ParallelAgent | Parallel enrichment (3 sources) | Inside SequentialAgent (step 2) | 0.90 |
| LoopAgent | Retry on enrichment failure | Inside ParallelAgent (per source) | 0.88 |
| CustomAgent (HITL) | Human review for high-severity | Inside SequentialAgent (step 4) | 0.85 |

**Adjacency validation:** ✅ Passed. LoopAgent inside ParallelAgent is valid. LoopAgent does NOT nest inside another LoopAgent.

**Composition source:** "First, the agent extracts... Then, in parallel, it enriches from three sources... If any enrichment fails, retry up to 3 times... Finally, a human reviews high-severity claims."

---

## 3. Agent Topology

| Agent | Class | Parent | Skills | Tools |
|---|---|---|---|---|
| fnol_coordinator | SequentialAgent | (root) | — | — |
| extract_details | LlmAgent | fnol_coordinator | fnol-extraction | claims-db-mcp |
| enrich_policy | LlmAgent | parallel_enrichment | policy-lookup | policy-api-mcp |
| enrich_vehicle | LlmAgent | parallel_enrichment | vehicle-lookup | vehicle-api-mcp |
| enrich_weather | LlmAgent | parallel_enrichment | weather-lookup | weather-api-mcp |
| parallel_enrichment | ParallelAgent | fnol_coordinator | — | — |
| severity_classifier | LlmAgent | fnol_coordinator | severity-rules | — |
| human_review | CustomAgent | fnol_coordinator | hitl-routing | review-queue-mcp |

---

## 4. Component Diagrams

![FNOL Claims Agent — Component Diagram](fnol-component-diagram.png)

*Editable source: [fnol-component-diagram.drawio.xml](fnol-component-diagram.drawio.xml) — open in draw.io to modify*

This diagram shows the agent topology with MCP connections, A2A boundaries, and infrastructure components. The SA should verify:
- Agent hierarchy matches the pattern composition (§2)
- MCP connections point to the correct endpoints
- A2A boundaries are correctly marked (external vs internal)

---

## 5. Tool Bindings

| Tool | Type | Endpoint | Agent | Discovered via | Confidence |
|---|---|---|---|---|---|
| claims-db-mcp | MCP Server | mcp://claims-db.internal:8080 | extract_details | Vertex AI Search (tool registry) | 0.95 |
| policy-api-mcp | MCP Server | mcp://policy-api.internal:8080 | enrich_policy | Vertex AI Search (tool registry) | 0.92 |
| vehicle-api-mcp | MCP Server | mcp://vehicle-api.internal:8080 | enrich_vehicle | Vertex AI Search (tool registry) | 0.88 |
| weather-api-mcp | MCP Server | https://api.weather.gov/points | enrich_weather | Vertex AI Search (tool registry) | 0.90 |
| review-queue-mcp | MCP Server | mcp://review-queue.internal:8080 | human_review | Vertex AI Search (tool registry) | 0.85 |
| body-shop-a2a | A2A Agent | https://bodyshop.partner.com/a2a | severity_classifier | spec §6 "They operate their own" | 0.80 |

---

## 6. Skill References

| Skill | Version | Provenance SHA | Agent | Use when | Do not use when |
|---|---|---|---|---|---|
| fnol-extraction | 2.1.0 | sha256:abc123 | extract_details | Extracting claim details from unstructured input | Structured API input |
| policy-lookup | 1.4.0 | sha256:def456 | enrich_policy | Looking up policy details by policy number | Policy number not available |
| vehicle-lookup | 1.2.0 | sha256:ghi789 | enrich_vehicle | VIN-based vehicle details | No VIN provided |
| weather-lookup | 1.0.0 | sha256:jkl012 | enrich_weather | Weather at incident location/time | Indoor incidents |
| severity-rules | 3.0.0 | sha256:mno345 | severity_classifier | Classifying claim severity | Already classified |
| hitl-routing | 1.1.0 | sha256:pqr678 | human_review | Routing high-severity to human queue | Low/medium severity |

---

## 7. MCP Server Configs

| MCP Server | Auth Method | Endpoint | Timeout | Retry |
|---|---|---|---|---|
| claims-db-mcp | mTLS | mcp://claims-db.internal:8080 | 30s | 3 |
| policy-api-mcp | OAuth 2.0 | mcp://policy-api.internal:8080 | 15s | 2 |
| vehicle-api-mcp | API Key | mcp://vehicle-api.internal:8080 | 15s | 2 |
| weather-api-mcp | None (public) | https://api.weather.gov/points | 10s | 1 |
| review-queue-mcp | mTLS | mcp://review-queue.internal:8080 | 60s | 1 |

---

## 8. Infrastructure Modules

| Module | Source Repo | Version | Agent/Component | DR Aware |
|---|---|---|---|---|
| tf-agentic-pilot-cold | github.com/company/tf-agentic-pilot-cold | v2.3.0 | Cloud Run (all agents) | ✅ |
| tf-apigee-gateway | github.com/company/tf-apigee-gateway | v1.8.0 | Apigee Runtime Gateway | ✅ |
| tf-cloud-sql | github.com/company/tf-cloud-sql | v3.1.0 | Claims DB | ✅ |
| tf-secret-manager | github.com/company/tf-secret-manager | v1.2.0 | All secrets | ✅ |
| tf-vpc-sc | github.com/company/tf-vpc-sc | v2.0.0 | VPC Service Controls | ✅ |

---

## 9. Business Rules

### extract_details (FunctionTool)

**IF** claim_type == "auto" **AND** police_report_number is provided
**THEN** validate police_report_number format (XX-YYYYYYY) and attach to claim record

**IF** claim_type == "auto" **AND** injuries_reported == true
**THEN** set priority = "HIGH" and route to bodily_injury queue

**IF** damage_estimate > $10,000
**THEN** require_photos = true, require_adjuster_inspection = true

### severity_classifier (FunctionTool)

**IF** injuries_reported == true **OR** damage_estimate > $25,000 **OR** fatality == true
**THEN** severity = "HIGH", route to human_review

**IF** damage_estimate > $5,000 **AND** damage_estimate <= $25,000
**THEN** severity = "MEDIUM", auto-process with audit flag

**IF** damage_estimate <= $5,000 **AND** injuries_reported == false
**THEN** severity = "LOW", auto-process

### Transformation Rules

| Source field | Target field | Formula |
|---|---|---|
| (auto-generated) | claim_number | `"CLM-" + YEAR(NOW()) + "-" + LPAD(SEQUENCE, 7, "0")` |
| damage_estimate | damage_category | `IF damage_estimate > 25000 THEN "major" ELSE IF damage_estimate > 5000 THEN "moderate" ELSE "minor"` |
| incident_date + incident_location | weather_lookup_key | `FORMAT(incident_date, "YYYY-MM-DD") + ":" + incident_location.zip_code` |
| policy_number | policy_lookup_format | `UPPER(TRIM(policy_number))` — normalize before API call |

---

## 10. NFRs

| NFR | Target | Source |
|---|---|---|
| Availability | 99.95% | plan.md |
| RTO | 4 hours (Pilot Light — Cold Standby) | plan.md |
| RPO | 1 hour | plan.md |
| Peak TPS | 500 claims/hour | spec.md §3 |
| P95 latency (end-to-end) | < 30 seconds | spec.md §3 |
| P95 latency (enrichment, per source) | < 5 seconds | spec.md §3 |
| Data classification | Confidential PII (claims data) | spec.md §4 |
| Compliance regimes | SOC 2, PCI-DSS | plan.md |
| Concurrent users | 50 adjusters | spec.md §3 |
| Data retention | 7 years (regulatory) | spec.md §4 |

---

## 11. Architecture Decisions Log

| ID | Decision | Status | Rationale | Consequences |
|---|---|---|---|---|
| ADL-001 | Use ECS Fargate via Cloud Run for all agents | Accepted | Simpler ops model, no cluster management, GA with SLA | Limited to 4 vCPU per task |
| ADL-002 | Use Cloud SQL for claims DB (not AlloyDB) | Accepted | Transactional workload, cost-effective, HA auto-failover | No columnar engine for analytics |
| ADL-003 | Use A2A for body shop integration | Accepted | "They operate their own" — external domain, separate data custody | Latency depends on partner SLA |
| ADL-004 | ParallelAgent for enrichment (not sequential) | Accepted | 3 independent sources, no data dependency between them | All-or-nothing failure mode |
| ADL-005 | Pilot Light — Cold Standby DR strategy | Accepted | RPO 1 hour, RTO 4 hours, cost-optimized for Tier-2 application | DR region has minimal compute until failover |

---

## 12. Tech Stack

| Layer | Components |
|---|---|
| Frontend | N/A (API-only agent) |
| Agent runtime | Cloud Run (GA) + Google ADK (Python) |
| Gateway | Apigee Runtime Gateway (GA) |
| Data | Cloud SQL (claims DB) + Secret Manager |
| Integration | 5 MCP Servers + 1 A2A Agent (body shop) |
| Security | Model Armor + VPC-SC + CMEK + Workload Identity |
| Observability | Dynatrace (APM) + Splunk (SIEM) + Arize Phoenix (traces) |
| CI/CD | Jenkins (infra) + Harness (deploy + 3-phase EvalOps) |
| IaC | Terraform (company modules from GitHub repos) |

---

## 13. HA/DR Views

![FNOL Claims Agent — HA/DR Lifecycle Diagram](fnol-hadr-diagram.png)

*Editable source: [fnol-hadr-diagram.drawio.xml](fnol-hadr-diagram.drawio.xml) — open in draw.io to modify*

**DR Strategy:** Pilot Light — Cold Standby (selected in plan.md)

| Lifecycle Scenario | Primary (us-east1) | DR (us-west1) | Trigger |
|---|---|---|---|
| Initial Provisioning | All resources active | Cloud SQL read replica + minimal infra | terraform apply |
| Component Failure (HA) | Auto-heal within region | No action | Cloud Run auto-restart |
| DR Failover | Traffic shifted to DR | Scale up compute, promote read replica | Manual or automated health check |
| DR Failback | Restore primary | Scale down, re-sync data | Manual verification |

**RTO:** 30–60 minutes (Cold Standby scale-up time)
**RPO:** 1 hour (Cloud SQL cross-region replication lag)

---

## 14. Sequence Diagrams

### Happy Path — FNOL Claim Submission

```mermaid
sequenceDiagram
    autonumber
    participant User as Adjuster
    participant GW as Apigee Gateway
    participant Coord as fnol_coordinator
    participant Extract as extract_details
    participant DB as claims-db-mcp
    participant Par as parallel_enrichment
    participant Policy as enrich_policy
    participant Vehicle as enrich_vehicle
    participant Weather as enrich_weather
    participant Sev as severity_classifier
    participant HR as human_review

    User->>GW: POST /api/v1/claims (unstructured claim text)
    GW->>Coord: Route to fnol_coordinator

    Note over Coord: Step 1: Extract details
    Coord->>Extract: delegate(claim_text)
    Extract->>DB: query existing policy
    DB-->>Extract: policy_record
    Extract-->>Coord: extracted_details{policy_no, vin, location, date, damage_est}

    Note over Coord: Step 2: Parallel enrichment
    Coord->>Par: delegate(extracted_details)
    par Parallel enrichment
        Par->>Policy: enrich(policy_no)
        Policy-->>Par: policy_details
    and
        Par->>Vehicle: enrich(vin)
        Vehicle-->>Par: vehicle_details
    and
        Par->>Weather: enrich(location, date)
        Weather-->>Par: weather_conditions
    end
    Par-->>Coord: enriched_claim

    Note over Coord: Step 3: Classify severity
    Coord->>Sev: classify(enriched_claim)
    Sev-->>Coord: severity=HIGH

    Note over Coord: Step 4: Human review (HIGH severity)
    Coord->>HR: route_to_human(enriched_claim, severity=HIGH)
    HR-->>Coord: review_decision{approved, adjuster_notes}

    Coord-->>GW: claim_response{claim_id, status, severity, review}
    GW-->>User: 200 OK + claim summary
```

### Error Path — Enrichment Failure with Retry

```mermaid
sequenceDiagram
    autonumber
    participant Par as parallel_enrichment
    participant Policy as enrich_policy
    participant Loop as LoopAgent (retry)

    Par->>Policy: enrich(policy_no)
    Policy-->>Par: ERROR 503 (service unavailable)
    Par->>Loop: retry(enrich_policy, policy_no)
    Loop->>Policy: enrich(policy_no) [attempt 2]
    Policy-->>Loop: ERROR 503
    Loop->>Policy: enrich(policy_no) [attempt 3]
    Policy-->>Loop: policy_details
    Loop-->>Par: policy_details (after 3 attempts)
```

---

## 15. Evaluation Config

| Parameter | Value |
|---|---|
| Pre-commit eval threshold | 10% regression blocks commit |
| Golden dataset minimum | 10 entries per agent, 3 edge cases, 1 negative |
| AutoSxS baseline | Current production version |
| HITL triage threshold | Confidence < 0.7 OR edge case flagged |
| Phase A quality gates | Arize precision ≥ 0.85, recall ≥ 0.80 |
| Phase B comparison | ≥ 95% parity with baseline on golden dataset |
| Phase C reviewer pool | 3 SMEs from claims team |

---

## 16. Screening Config

| Layer | Scope | Policy |
|---|---|---|
| Layer A | Per-source screening | User prompt: block on PII injection. Tool result: block on SQL injection. A2A response: block on prompt injection. |
| Layer B | Assembled context | Compositional attack detection: individually safe inputs that combine to attack |
| Layer C | Response screening | Block PII in response. Block hallucinated policy numbers. |
| Remediation | Source-specific | User prompt → block request. Tool → quarantine + alert. A2A → disconnect agent. |

---

## 17. Pipeline Configs

| Pipeline | Template | Parameters |
|---|---|---|
| Infrastructure (Jenkins) | agent-infra-plan-apply-v3 | project=fnol-claims, regions=[us-east1, us-west1], dr_strategy=pilot-cold |
| Deployment (Harness) | agent-deploy-canary-v2 | service=fnol-coordinator, canary_percent=10, rollback_threshold=1% |
| EvalOps (Harness) | agent-evalops-3phase-v1 | golden_dataset=fnol-golden.json, hitl_reviewers=3 |

---

## 18. Confidence Scores

| Section | Confidence | Explanation |
|---|---|---|
| Pattern composition | 0.95 | Strong ordering words in spec. Clear sequential + parallel + retry + HITL signals. |
| Agent topology | 0.92 | All agents mapped. One A2A boundary (body shop) identified from "They operate their own." |
| Tool bindings | 0.88 | 5/6 tools found in registry. weather-api-mcp is public (lower confidence on availability). |
| Skill references | 0.90 | All skills found in catalog. severity-rules v3.0.0 is latest. |
| Infrastructure modules | 0.95 | All TF modules found in GitHub repos. Version-pinned. |
| Business rules | 0.85 | Rules extracted from spec §7. Some thresholds may need SA validation. |
| Overall | 0.92 | High confidence. SA should verify: body-shop A2A endpoint, damage thresholds in biz rules. |

---

*Generated by Blueprint Advisor MCP Server · AgentCatalyst v1.0*
```

---

## 4. Governance Guardian Integration

> **Related Architecture Sections:**
> - §8 Infrastructure Modules URLs are consumed by the `company-terraform` overlay skill during `/catalyst.generate` — see Architecture Document, Layer 3 (IaC generation flow) for how the coding agent reads module interfaces via GitHub MCP Server and generates compliant Terraform.
> - The blueprint is delivered via `blueprint_result` over OAuth 2.1-authenticated MCP — see Architecture Document, Layer 2 Security for the full Entra ID authentication sequence diagram.
> - Blueprint generation task state is stored in AlloyDB — see Architecture Document, Layer 2 (Task Store tenant isolation).
> - The Governance Guardian reads all 7 artifact types from this file — see Governance Guardian Architecture Extension for the assessment flow and scorecard format.

With `app-blueprint.md` as the single source of truth, the `/catalyst.assess` prompt file simplifies dramatically:

**Before (YAML + scattered files):** The coding agent had to hunt for drawio files, NFR documents, ADL directories, and assemble them into a JSON package.

**After (markdown):** The coding agent reads `app-blueprint.md` and extracts sections by header. The PNGs are referenced inline — the coding agent reads them from the workspace path specified in the `![...]()` reference.

The updated `/catalyst.assess` extraction becomes:

| Artifact | Extraction method |
|---|---|
| TSA component diagram | Read the PNG file referenced in §4 `![...](fnol-component-diagram.png)` |
| HA/DR views | Read the PNG file referenced in §13 `![...](fnol-hadr-diagram.png)` + parse the lifecycle table |
| Sequence diagrams | Extract inline mermaid code blocks from §14 |
| NFRs | Parse the table in §10 |
| Architecture Decisions Log | Parse the table in §11 |
| Tech stack | Parse the table in §12 |
| Patterns used | Parse the table in §2 |
