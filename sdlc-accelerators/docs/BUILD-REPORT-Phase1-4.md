# SDLC Accelerators — Phase 1-4 Build Report

## Summary

All four phases generated and validated against the FNOL reference example. **13 tests passing, clean lint.** The deterministic and structural code is real and tested; the two judgment cores (meta-skill reasoning, Governance Guardian rubric) are runnable harnesses that enforce the human-authored boundary in code rather than fabricating IP.

| Phase | Scope | State |
|---|---|---|
| 1 | JSON schemas | ✅ Complete — 9 schemas, FNOL-validated |
| 2 | Solution Accelerator MCP Server | ✅ Structural complete — deterministic stages tested; reasoning stages are authored extension points |
| 3 | Governance Guardian, accelerator-cli, IaC, CI/CD | ✅ Complete — CLI generates 14 files from FNOL; Guardian extracts 9 sections |
| 4 | Domain skill, overlay skills, code templates | ✅ Agentic-AI archetype complete and validated |

---

## Phase 1 — Schemas (9 files, all FNOL-validated)

| Schema | Contract |
|---|---|
| `app-blueprint.schema.json` | The full app-blueprint.json structure — validated against FNOL (caught real type mismatches in pipeline_configs, nfr_targets, pattern_composition, metadata during build) |
| `blueprint_start/status/result.json` | Solution Accelerator async MCP tool I/O |
| `refresh.json` | Bidirectional sync I/O |
| `assess_start/status/result.json` | Governance Guardian I/O |
| `record_tech_debt.json` | recordTechDebt signal I/O |

The schema build itself surfaced 5 structural corrections where the original schema assumptions didn't match the real FNOL data — exactly the validation value schemas exist to provide.

---

## Phase 2 — Solution Accelerator (18 Python files)

| Module | State |
|---|---|
| `models/blueprint.py` | ✅ Pydantic models; FNOL loads through them (root=fnol_coordinator, 8 bindings, 5 rules) |
| `clients/base.py` | ✅ Real retry + timeout + structured-logging wrapper |
| `clients/{vertex_search,apigee_hub,eraser_io,alloydb_taskstore,adr_store}.py` | Interface real; external calls STUB-marked TODO for live wiring |
| `pipeline/dsl_builder.py` | ✅ Deterministic Eraser.io DSL construction — byte-stable, tested |
| `pipeline/orchestrator.py` | ✅ `run_deterministic_stages()` fully works (2 diagrams from FNOL); `run_pipeline()` reaches the reasoning boundary |
| `reasoning/recommend_architecture.py` | ✅ Single RAG-grounded LlmAgent reasoning stage; `reason()` raises NotImplementedError (curated system prompt is human-authored) |
| `server/{task_store,app}.py` | ✅ Async task lifecycle; handlers unit-testable; transport wiring TODO |

**Honest boundary:** the reasoning is not fabricated. recommend_architecture does RAG retrieval and shapes output, but the judgment (curated system prompt + golden dataset) raises NotImplementedError until wired.

**IP CORRECTION:** an earlier draft wrongly placed AgentForge's four meta-skills (MS1-MS4) inside this pipeline. Corrected — SDLC Accelerators uses **RAG + skill-constrained generation**, a single recommend_architecture reasoning stage. Meta-skills, STL, and signed Design Contracts are AgentForge (AnchorOps) IP with **zero overlap** here. This separation is deliberate and legally load-bearing.

---

## Phase 3 — Guardian, CLI, IaC, CI/CD

### accelerator-cli (6 files) — the production-code generator
- `generator/adk_renderer.py` — the validated agentic-AI renderer (absorbed from the domain skill)
- `generator/engine.py` — archetype dispatch
- `commands/generate.py` — governance gate + generation
- **Generates 14 valid Python files from the FNOL blueprint, byte-identical across runs**
- Governance gate blocks on showstopper signal ✅

### Governance Guardian (5 files)
- `extraction/sections.py` — ✅ extracts all 9 sections from the FNOL app-blueprint.md, deterministic
- `assessment/engine.py` — harness + scorecard structures real; `assess_sections()` rubric is the human-authored extension point (raises until authored); `classify_finding()` implements the one platform-level rule (critical→showstopper)

### IaC (3 Terraform modules)
- `cloud-run-agent`, `alloydb`, `apigee-proxy` — scaffolds with CMEK, Binary Authorization, scaling

### CI/CD
- `.github/workflows/ci.yaml` — lint + test
- `iac/environments/prod/cloudbuild.yaml` — build + cosign/Binary Auth (NEVER-SWAPPABLE) markers

---

## Phase 4 — Skills + Templates (agentic-AI archetype)

| Artifact | State |
|---|---|
| `skills/domain-skills/agentic-ai-adk.SKILL.md` | ✅ Authored — type→ADK mappings, 7 production rules, validation checklist |
| `templates/code/agentic-ai-adk/*.j2` (10 templates) | ✅ Sequential, Parallel, LlmAgent (+LoopAgent), HITL, FunctionTools, Model Armor, mcp_clients, a2a_clients, agent_identity, main |
| `skills/overlay-skills/{security,observability,ci-cd}.SKILL.md` | ✅ Authored |
| `examples/fnol/generated-sample/` | ✅ 14-file golden reference, regenerated |

**Validated output:** the agentic-AI skill generates the full FNOL app — coordinator (SequentialAgent, delegation-only), parallel enrichment (3 LoopAgent-wrapped), Model Armor on 6 agents (output on 3), MCP/A2A wiring, 6 Agent Identities. All valid Python, deterministic.

**Known scaffolding gaps (next authoring):**
- FunctionTool rule predicates are TODO comments — prose→logic extraction needs human verification
- Domain skills for microservice/pipeline/api archetypes follow the agentic-AI pattern (not yet authored)

---

## Test Suite (13 passing)

| File | Covers |
|---|---|
| `test_phase1_schemas.py` | app-blueprint schema validates FNOL; all MCP schemas are valid JSON Schema |
| `test_phase2_pipeline.py` | models load FNOL; DSL deterministic; 2 diagrams; reasoning boundary raises |
| `test_phase3_cli.py` | CLI generates 14 files; byte-identical; gate blocks showstopper; output compiles |
| `test_phase3_guardian.py` | extracts 9 sections; critical→showstopper; assessment boundary raises |

---

## What remains human-authored (by design)

1. **recommend_architecture reasoning** — wire the company-curated system prompt + golden dataset into the Solution Accelerator LlmAgent (single RAG stage; NOT meta-skills — those are AgentForge IP)
2. **Governance Guardian assessment rubric** — the EA scoring/classification logic
3. **FunctionTool predicates** — verify extracted logic against spec.md §7
4. **Additional archetype skills** — microservice, pipeline, api
5. **Live wiring** — replace client STUBs, bind MCP transport, deploy IaC

These are the genuine judgment/IP and integration points. Everything deterministic, schema-driven, and structural is built and tested.
