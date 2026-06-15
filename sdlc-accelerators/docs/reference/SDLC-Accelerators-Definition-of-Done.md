# SDLC Accelerators — Definition of Done (v2, corrected)

Corrects v1: the Solution Accelerator **system prompt is already authored** (in the Developer Guide, now extracted into the repo), and the **FNOL spec.md/plan.md exist** (also from the Developer Guide). These move from "to author" to "authored." The genuine remaining authoring task for the reasoning stage is the **RAG corpus**, not the prompt.

Legend: 🟢 done & tested · 🟡 scaffold/partial · 🔴 not started · **Authoring** (your IP) · **Wiring** (mechanical, Claude Code-assisted)

---

## Already done (deterministic / structural — built & tested)

| Component | State |
|---|---|
| JSON schemas (9) | 🟢 FNOL + contract-review validate |
| Pydantic models, DSL builder, diagram pipeline | 🟢 |
| accelerator-cli generator + governance gate | 🟢 generates 2 different apps, byte-identical |
| agentic-AI domain skill + 11 templates | 🟢 validated on 2 use cases |
| Governance Guardian 9-section extractor | 🟢 |
| Overlay skills | 🟢 |
| **Solution Accelerator system prompt** | 🟢 **authored** (greenfield-system-prompt.md), loaded by recommend_architecture.py |
| **FNOL spec.md + plan.md** | 🟢 **authored** (from Developer Guide FNOL-T1/T2) |
| Test suite | 🟢 18 passing |

---

## Remaining work — sequenced

### 1. RAG corpus — pattern / skill / tool / agent-card catalogs
**Type: AUTHORING (highest priority)** · 🔴 not started
The system prompt *instructs* the agent to "search the pattern catalog," "discover tools and agents," "match skills." Those catalog **contents** must be ingested into Vertex AI Search + the GitHub skills catalog.
**What you author:** the 11 agentic pattern documents, the skill catalog entries (with SHA/version provenance), tool/MCP metadata, and A2A agent cards.
**Why first:** the prompt is written and loads, but `retrieve()` returns empty until the corpus exists — so reasoning can't run end-to-end. This is now the load-bearing gap (not the prompt).
**Done when:** Vertex AI Search returns relevant patterns/tools for a spec's signals, and `recommend_architecture.retrieve()` returns non-empty.

### 2. Wire the system prompt + RAG context into a live LlmAgent
**Type: WIRING** · 🟡 prompt loads; live LlmAgent binding pending
`recommend_architecture.reason()` loads the authored prompt and the retrieved context but does not yet call a live LlmAgent.
**Claude Code can do this** given the ADK LlmAgent API + the loaded prompt.
**Done when:** a real spec.md + plan.md flows through blueprint_start → valid app-blueprint.json (schema-passing).

### 3. Golden dataset for the reasoning stage
**Type: AUTHORING** · 🔴 not started
Eval examples that validate recommend_architecture's outputs (spec → expected pattern/tool composition).
**What you author:** curated spec→blueprint pairs (the FNOL pair is the first).
**Done when:** the EvalOps Phase-1 threshold can be measured against the dataset.

### 4. Governance Guardian assessment rubric
**Type: AUTHORING** · 🟡 harness + scorecard exist, `assess_sections()` raises
The EA scoring per §1–§9, showstopper-vs-tech-debt classification, weights.
**Done when:** an app-blueprint.md produces a scorecard + classified findings; showstoppers block generation.

### 5. FunctionTool predicates
**Type: AUTHORING (per use case, small)** · 🟡 shells generate, bodies are TODO
Verify each extracted IF/THEN predicate against spec §7 and fill the body.
**Done when:** generated function_tools.py has executable logic.

### 6. The three remaining archetype skills
**Type: AUTHORING (follows agentic-AI pattern)** · 🔴 not started
microservice, pipeline, api-first — each a domain SKILL.md + templates, drafted from the agentic-AI reference.
**Done when:** each generates + AST-validates against its own committed fixture.

### NEW (Phase 5): Terraform generation ✅ DONE, PRS scanner ✅ DONE, EvalOps gate logic ✅ (SDK stub), Harness pipeline ✅ reference
See docs/BUILD-REPORT-Phase5-Pipeline.md. The agent Terraform template, the constitution-enforcing PRS scanner, the golden-dataset/eval gate, and the 5-stage reference Harness pipeline are built (Terraform + scanner fully tested).

### 7. Live wiring — client integrations
**Type: WIRING** · 🟡 interfaces real, calls stubbed
Replace stubs in clients/ with real SDK calls (Vertex AI Search, Apigee, Eraser.io, AlloyDB).

### 8. Live wiring — MCP transport + OAuth + deploy
**Type: WIRING** · 🟡 handlers testable, transport binding TODO
Bind handlers to the MCP SDK, add OAuth 2.1 + Entra ID, deploy via IaC to Cloud Run.

### 9. End-to-end integration test
**Type: WIRING** · 🔴
FNOL spec.md → blueprint → assess → generate → PR, through the live platform.

---

## Summary

| # | Item | Type | v1 said | v2 (corrected) |
|---|---|---|---|---|
| — | System prompt | — | "to author (highest priority)" | ✅ **authored & loaded** |
| — | FNOL spec.md/plan.md | — | implied missing | ✅ **authored** (from dev guide) |
| 1 | RAG corpus | Authoring | (was item 2) | **now highest priority** |
| 2 | Wire prompt → LlmAgent | Wiring | — | new (small) |
| 3 | Golden dataset | Authoring | — | surfaced |
| 4 | Governance Guardian rubric | Authoring | yes | unchanged |
| 5 | FunctionTool predicates | Authoring | yes | unchanged |
| 6 | 3 more archetypes | Authoring | yes | unchanged |
| 7–8 | Live wiring | Wiring | yes | unchanged |
| 9 | E2E test | Wiring | yes | unchanged |

**Corrected headline:** the reasoning stage's **prompt is authored and loaded** — what's missing there is the **RAG corpus** (the catalog contents the prompt searches) plus the **live LlmAgent binding**. The remaining authoring cores are now: the RAG corpus, the Governance Guardian rubric, the golden dataset, per-app predicates, and the three other archetypes. My earlier claim that "recommend_architecture's prompt is the highest-priority authoring gap" was wrong — the prompt already exists; the catalog it searches does not.
