# Build Report — Reasoning-Time Assembly (assemble_blueprint)

Implements the deterministic assembly that turns composed selections into the three artifacts.
**35 tests passing (5 new), clean lint.**

## What this implements
The architecture's two-stage flow: recommend_architecture (LLM) produces validated
**ArchitectureSelections** → validate_composition (adjacency) → **assemble_blueprint**
(DETERMINISTIC, no LLM) produces:
1. `app-blueprint.md` — §1–§9 governance sections (PRIMARY artifact)
2. `app-blueprint.json` — derived, schema-conformant (DERIVED artifact)
3. Eraser DSL → `component-topology.drawio.xml`/`.png` + `hadr-lifecycle.*`

## Components (services/solution-accelerator/src/assembly/)
- `selections.py` — ArchitectureSelections: the contract between reasoning and assembly
  (patterns, agent tree, tools, skills w/ SHA provenance, business rules, config)
- `derive_json.py` — selections → schema-conformant app-blueprint.json (deterministic, hashes)
- `render_markdown.py` — selections → §1–§9 governance markdown (no LLM)
- `assemble.py` — assemble_blueprint(): ties md + json + Eraser DSL together

## Validations (all tested)
- ✅ Derived JSON validates against schemas/app-blueprint.schema.json
- ✅ Generated .md round-trips: Governance Guardian extractor reads back all 9 sections
- ✅ Assembly is deterministic (same selections → byte-identical md/json/dsl)
- ✅ Eraser DSL constructed from topology for both component + HA/DR diagrams

## Demonstration
`examples/fnol/assembled-demo/` — a full assembled set (app-blueprint.md, app-blueprint.json,
diagrams/*.drawio.xml + *.dsl) produced from FNOL selections, end to end.

## Scope honesty
- The assembly (md + json + DSL construction) is real, deterministic, and tested.
- recommend_architecture FILLING the selections is the human-authored reasoning (system prompt +
  RAG corpus) — that boundary is unchanged. This build implements everything DOWNSTREAM of
  reasoning: given selections, produce the artifacts.
- Eraser.io headless .png rendering is wired through the client (TODO live); the .drawio.xml/.dsl
  and the .md/.json are fully produced.
