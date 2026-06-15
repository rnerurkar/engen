# CLAUDE.md — Solution Accelerator MCP Server

> Service-specific context. Read the root `CLAUDE.md` first for platform-wide conventions.

## Role

The spine of the platform. Takes `spec.md` + `plan.md`, runs a background reasoning pipeline, and produces the `app-blueprint` package (`.md` PRIMARY + `.json` DERIVED + `.drawio.xml` + `.png` diagrams). Exposed as an MCP Server on Cloud Run.

## MCP tools (contracts in `schemas/`)

| Tool | Sync/Async | Contract |
|---|---|---|
| `blueprint_start(spec, plan)` | Async — returns taskId | `schemas/blueprint_start.json` |
| `blueprint_status(taskId)` | Sync poll | `schemas/blueprint_status.json` |
| `blueprint_result(taskId)` | Sync retrieve | `schemas/blueprint_result.json` |
| `assemble_blueprint(...)` | Deterministic | `schemas/assemble_blueprint.json` |
| `validate_composition(...)` | Deterministic | `schemas/validate_composition.json` |
| `refresh(md, drawio, spec, plan)` | Sync — bidirectional sync | `schemas/refresh.json` |

## Background pipeline (the order matters)

```
0. validate_spec                  — quality gate, BLOCK if critical signals missing
1. recommend_architecture         — single RAG-grounded LlmAgent reasoning stage
                                    (company-curated system prompt + Vertex AI Search RAG)
2. discover_integrations          — Apigee API Hub query (MCP servers + A2A + REST)
3. adr_compliance_check           — deterministic
4. resolve_modules                — GitHub TF module repos
5. Construct Eraser.io DSL        — deterministic serialization of topology
6. Eraser.io API → component-topology.drawio.xml + .png
7. Eraser.io API → hadr-lifecycle.drawio.xml + .png
8. assemble_blueprint            — .md + .json from all above
9. bundle → Task Store
```

**IP BOUNDARY — critical:** SDLC Accelerators uses **RAG + skill-constrained generation**.
It does NOT use meta-skills, STL (Structured Topology Language), or signed Design Contracts.
Those are **AgentForge (AnchorOps) constructs with ZERO overlap here** — keeping them out of
this codebase is a deliberate IP-separation requirement. The single reasoning stage
(`recommend_architecture`) is one LlmAgent steered by a human-authored company-curated
system prompt + golden dataset — not four meta-skills.

## Bidirectional refresh (`refresh` tool)

`app-blueprint.json` is the reconciliation hub. Both `.md` (prose) and `.drawio.xml` (visual) sync THROUGH it.
- Case A (.md changed) → regenerate .drawio.xml + .png from .json topology
- Case B (.drawio changed) → parse diagram, update .json, LLM updates .md §2 narrative
- Case C (both) → diff against last-known .json, auto-merge agreements, surface conflicts

Detect changes via `.accelerator-hashes` (SHA-256). See `docs/architecture.md` refresh section + `refresh-sync-flow.png`.

## Key dependencies (typed client wrappers required)

- AlloyDB (task store) — async, RLS, 24h retention
- Vertex AI Search (pattern + tool catalog)
- Apigee API Hub (A2A + REST discovery)
- Eraser.io headless (DSL → .drawio.xml + .png)
- ADR Constraint Store (AlloyDB + Rule UI)

## Auth

OAuth 2.1 + Entra ID. Single audience scope `sdlc-accelerators.mcp`. Validate token audience on every request. Workload Identity for GCP service-to-service.

## Tests

Unit-test each pipeline stage in isolation with mocked clients. The DSL construction (stage 8) and assemble_blueprint (stage 11) are deterministic — test them against the FNOL fixture with golden outputs.
