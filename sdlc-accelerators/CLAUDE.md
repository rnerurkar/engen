# CLAUDE.md — SDLC Accelerators Platform

> This file is read at the start of every Claude Code session. It establishes the conventions, constraints, and architecture every generation must respect. Per-service `CLAUDE.md` files add service-specific detail; the nearest one to the file being edited wins.

## Model & working mode

Use **Claude Opus 4.8** for this repo — the generation tasks (MCP servers, deterministic transforms, schema-driven code) benefit from its planning depth. Set it with `/model opus` in Claude Code, or run `claude --model claude-opus-4-8`.

Default to **plan mode** for any multi-file module: present the approach, get approval, then generate. Generate code and tests together, run the tests, and self-correct before moving on.

## What this platform is

SDLC Accelerators (internal name; formerly AgentCatalyst) is an employer-internal, spec-driven multi-agent development platform on GCP. A developer writes a `spec.md` and `plan.md`, the **Solution Accelerator** turns them into a structured `app-blueprint` (markdown + JSON + diagrams), the **Governance Guardian** assesses it against enterprise architecture standards, and skill-guided generation produces born-compliant application code. The platform is archetype-agnostic: the same Solution Accelerator + skills + governance produce agentic AI agents, microservices, event-driven pipelines, or API-first services depending on the preset.

Full narrative context: `docs/architecture.md` (the architecture doc), `docs/developer-guide.md`, `docs/operations-runbook.md`. Read those for the "why"; this file is the "how" for generation.

## Tech stack (pinned)

| Layer | Choice | Notes |
|---|---|---|
| Primary language (services) | Python 3.12 | Solution Accelerator, Governance Guardian, accelerator-cli |
| Agent framework | Google ADK 2.0 | SequentialAgent, ParallelAgent, LoopAgent, graph workflows |
| MCP protocol | 2025-03-26 | Async MCP Tasks pattern for long-running tools |
| Runtime | Cloud Run | Containerized, OAuth 2.1 + Entra ID |
| Task store | AlloyDB (PostgreSQL-compatible) | 24h retention, row-level security |
| Pattern/tool catalog | Vertex AI Search | NEVER-SWAPPABLE |
| Integration discovery | Apigee API Hub | A2A + REST discovery |
| Diagram rendering | Eraser.io headless → .drawio.xml + .png | DSL serialized from topology |
| IaC | Terraform | Company module repos via GitHub MCP Server |
| CI/CD | Cloud Build + Cloud Deploy | Downstream of this platform; also Jenkins/Harness at runtime |
| Observability | Cloud Monitoring, Cloud Logging, Cloud Trace | GCP-native defaults |
| Evaluation | Vertex AI Evaluation SDK | EvalOps Phase 1-2 |
| Supply chain | cosign + Binary Authorization | NEVER-SWAPPABLE |
| Prompt/content safety | Model Armor | NEVER-SWAPPABLE |

## NEVER-SWAPPABLE components

Do not substitute, abstract behind a swappable interface, or "improve" these. They are fixed platform decisions:

- **cosign** — artifact signing
- **Binary Authorization** — deploy-time attestation enforcement
- **Vertex AI Search** — pattern and tool catalog retrieval
- **Model Armor** — prompt/response safety
- **The design-contract schema** — the canonical contract structure

If a task seems to require changing one of these, stop and flag it rather than working around it.

## Architecture: two governance gates only

This platform has exactly **two** governance gates: the **Design Gate** and the **Plan Gate**. Eval and promote stages are explicitly OUT OF SCOPE — they are handled downstream by the company CI/CD pipeline (Cloud Build/Cloud Deploy, and Jenkins/Harness at runtime). Do not generate eval-gate or promote-gate logic inside this platform.

## The three MCP servers / services

| Service | Directory | Role |
|---|---|---|
| Solution Accelerator MCP Server | `services/solution-accelerator/` | Turns spec.md + plan.md into app-blueprint. Tools: `blueprint_start/status/result`, `assemble_blueprint`, `validate_composition`, `refresh`. Async MCP Tasks. |
| Governance Guardian MCP Server | `services/governance-guardian/` | EA assessment engine. Tools: `assess_start/status/result`, `recordTechDebt`. Reads app-blueprint.md §1-§9. Independent, EA-owned logic. |
| accelerator-cli | `services/accelerator-cli/` | Python CLI. Deterministic scaffold + governance gate. Reads app-blueprint.json, generates project via company Jinja2 templates. |

## Protected identifiers — do NOT rename

These are stable API/artifact names. The product rebrand (AgentCatalyst → SDLC Accelerators) does NOT touch them:

- MCP tool names: `blueprint_start`, `blueprint_status`, `blueprint_result`, `assemble_blueprint`, `validate_composition`
- Artifact names: `app-blueprint.md`, `app-blueprint.json`
- `Governance Guardian` (component name)

Commands ARE rebranded: use `/accelerator.*` (not `/catalyst.*`).

## Directory conventions

```
services/<name>/src/      — service source
services/<name>/tests/    — pytest tests, mirror src/ structure
services/<name>/CLAUDE.md — service-specific generation context
schemas/                  — JSON Schemas (MCP contracts, app-blueprint, design-contract)
skills/domain-skills/     — per-archetype generation skills (agentic-ai-adk authored)
skills/domain-skills/     — per-archetype generation skills
skills/overlay-skills/    — security/observability/CI-CD overlays
templates/                — Jinja2 templates for spec, plan, blueprint
iac/modules/              — Terraform modules
commands/                 — /accelerator.* command pointers (real bodies in .specify/commands/)
.specify/                 — installable spec-kit preset (preset.yml, templates, commands, memory/constitution.md)
```

## Coding standards

- Python: type hints everywhere, `ruff` for lint/format, `pytest` for tests, `pydantic` v2 for schemas.
- Every public function has a docstring stating inputs, outputs, and side effects.
- MCP tools validate input against the JSON Schema in `schemas/` before processing.
- Async tools follow the MCP Tasks pattern: start returns a taskId, status polls, result retrieves. Never block.
- All external calls (AlloyDB, Vertex AI Search, Apigee, Eraser.io) go through a typed client wrapper with retry + timeout + structured logging.
- Secrets via Secret Manager only — never in code, env files committed, or logs.
- Every generated agent gets Model Armor callbacks and an Agent Identity (least-privilege capabilities derived from tool bindings).

## Testing requirement

Generate tests alongside code, not after. Every MCP tool, every client wrapper, every deterministic transform (DSL construction, blueprint assembly) has unit tests. The FNOL claims agent is the end-to-end integration test fixture.

## Reference artifacts — USE THESE as the generation pattern

This repo ships with spec-kit templates, command definitions, skill stubs, JSON schemas, and a complete FNOL worked example. They are the DEMONSTRATED reference — always prefer pattern-matching against them over inventing structure. Before generating any module, read the artifacts relevant to it:

| Artifact | Location | Use it when |
|---|---|---|
| spec template | `templates/spec/spec-template.md` | Generating spec parsing or `/speckit.specify` |
| plan template | `templates/plan/plan-template.md` | Generating plan parsing or `/speckit.plan` |
| app-blueprint template + worked FNOL | `templates/blueprint/app-blueprint-template-and-fnol-example.md` | Generating `assemble_blueprint`, the 9-section model, or the `.md`→`.json` derivation |
| `/accelerator.*` command defs | `commands/accelerator.{blueprint,assess,generate,refresh}.md` | Generating CLI command handlers |
| Reasoning stage | `services/solution-accelerator/src/reasoning/recommend_architecture.py` | Single RAG-grounded LlmAgent (curated prompt is human-authored). NO meta-skills — that's the external platform IP. |
| **Authored domain skill (agentic-AI)** | `skills/domain-skills/agentic-ai-adk.SKILL.md` + `templates/code/agentic-ai-adk/` | Generating ADK agent code — the FIRST authored skill, validated against FNOL |
| JSON schemas | `schemas/*.json` | Generating ANY MCP tool or the app-blueprint structure (read the schema FIRST) |
| **FNOL worked example** | `examples/fnol/` | The end-to-end golden reference for the WHOLE platform |

## The FNOL example is the golden reference

`examples/fnol/` contains the canonical input→output chain. Use it as both the pattern and the test fixture:

| File | Role |
|---|---|
| `examples/fnol/inputs/spec.md` | Golden input — the WHAT |
| `examples/fnol/inputs/plan.md` | Golden input — the HOW (technical) |
| `examples/fnol/outputs/app-blueprint.md` | Golden output — 9-section governance doc (PRIMARY) |
| `examples/fnol/outputs/app-blueprint.json` | Golden output — machine-readable (DERIVED) |
| `examples/fnol/diagrams/fnol-eraser-dsl-examples.md` | Golden output — both Eraser.io DSLs, fully worked |
| `examples/fnol/README.md` | Maps every artifact and how to use it |

Rules for using the FNOL example:
- Generating the **Solution Accelerator pipeline** → FNOL spec.md/plan.md are the test input; FNOL app-blueprint.md/.json are the expected output.
- Generating the **DSL construction (stage 8)** → the FNOL DSL examples are the golden output; given the FNOL topology, your serializer must reproduce them.
- Generating **accelerator-cli** → FNOL app-blueprint.json is the input; the generated project is the determinism golden tree.
- Generating the **Governance Guardian** → FNOL app-blueprint.md §1-§9 is the assessment fixture.

If a module can't process the FNOL example end-to-end, it isn't done.

A validated reference output exists at `examples/fnol/generated-sample/` — produced by the agentic-AI domain skill from the FNOL blueprint. The accelerator-cli golden-file test must reproduce it byte-for-byte.

## How to work in this repo

1. Read this file and the nearest per-service `CLAUDE.md`.
2. For any module, read the relevant schema in `schemas/` first — it is the contract.
3. Read the matching reference artifact above and the FNOL example for that module.
4. Use plan mode before multi-file changes; get approval on the approach.
5. Generate code + tests together; use the FNOL example as the test fixture; then run the tests.
6. Keep commits small and reviewable.
7. When a task touches a NEVER-SWAPPABLE component or seems to require changing the design-contract schema, stop and flag it.

## What NOT to generate

- No eval-gate or promote-gate logic (out of scope — downstream CI/CD owns it).
- No substitutes for NEVER-SWAPPABLE components.
- No renaming of protected identifiers.
- No `localStorage`/browser-storage assumptions (these are backend services).
- The reasoning *content* (the recommend_architecture curated system prompt) and the Governance Guardian assessment rubric are human-authored — scaffold the structure, but do not invent the judgment logic.
- **IP boundary:** never introduce meta-skills, STL, or signed Design Contracts here. Those are the external platform (AnchorOps) constructs. SDLC Accelerators = RAG + skill-constrained generation, zero overlap.
