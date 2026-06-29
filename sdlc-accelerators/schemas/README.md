# Schemas — The Contract Layer

JSON Schemas that pin down every interface. These are the source of truth for code generation: Claude Code reads the relevant schema BEFORE generating the module that implements or consumes it.

## To be populated (Phase 1)

| Schema | Describes |
|---|---|
| `blueprint_start.json` | Solution Accelerator blueprint_start tool I/O |
| `blueprint_status.json` | blueprint_status tool I/O |
| `blueprint_result.json` | blueprint_result tool I/O |
| `ingest_epic_start.json` | Solution Accelerator ingest_epic_start tool I/O (OPTIONAL Greenfield front door: Rally Epic → spec.md) |
| `ingest_epic_status.json` | ingest_epic_status tool I/O (phase: shaping → mapping) |
| `ingest_epic_result.json` | ingest_epic_result tool I/O (spec.md + Epic Signal Ledger + per-section confidence) |
| `epic-signal-ledger.schema.json` | The Epic Signal Ledger (Phase A output; section-keyed, span-traced) consumed by Phase B |
| `assemble_blueprint.json` | assemble_blueprint deterministic transform I/O |
| `validate_composition.json` | validate_composition I/O |
| `refresh.json` | Bidirectional refresh I/O (Case A/B/C) |
| `assess_start.json` | Governance Guardian assess_start I/O |
| `assess_status.json` | assess_status I/O |
| `assess_result.json` | assess_result (scorecard + findings) I/O |
| `record_tech_debt.json` | recordTechDebt I/O |
| `app-blueprint.schema.json` | The app-blueprint.json structure (adk_agent_tree, tool_bindings, data_flows, infra_modules, hadr_config, sequence_summary) |
| `design-contract.schema.json` | design-contract.json (states, attestations, lifecycle) — NEVER-SWAPPABLE |
| `app-blueprint-md.spec.md` | The 9-section .md template, field-level definitions |

Each schema includes the FNOL claims agent as a worked example.

## FNOL examples
Each schema should embed the FNOL case from `examples/fnol/` as its worked example, so Claude Code sees a populated instance alongside the schema.
