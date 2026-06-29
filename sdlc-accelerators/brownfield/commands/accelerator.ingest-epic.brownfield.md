# /accelerator.ingest-epic (Brownfield) — Rally Epic → integration-inventory spec.md

> Registered in the shared command surface at `.specify/commands/accelerator.ingest-epic.brownfield.md` (M-4). This copy is the brownfield-local source of truth.


Optional **front door** for the brownfield archetype, run BEFORE `/speckit.specify`. It turns a Rally
Epic into a signal-bearing brownfield migration `spec.md` (integration inventory) so the developer
**reviews** rather than authors. The CSA diagram remains the authoritative current-state source (see the
CSA Agent handoff, Architecture §7); ingestion pre-fills the integration inventory and NFRs from the Epic.

## Steps (coding agent)
1. Ask the developer for the Rally Epic FormattedID (capability-negotiated interview).
2. Fetch the Epic via the **Rally MCP server** (`.vscode/mcp.json`, Entra ID SSO — credentials stay in the
   IDE). Use the registered read tools (environment-specific — commonly `get_epic`, `query_epics`,
   `get_acceptance_criteria`; discover from the server). Capture `ObjectVersion` + `LastUpdateDate`.
3. Call the brownfield Solution Accelerator MCP tool `ingest_epic_start` with `{ epic: <content> }`
   (content only — no credentials). The server DELEGATES to the **Solution Accelerator Agent** (one ADK
   agent): Phase A runs its `create_epic_signal_ledger` FunctionTool (extractive, span-grounded), Phase B
   maps deterministically to the integration-inventory `spec.md`.
4. Poll `ingest_epic_status({ taskId })` every `pollInterval` ms; report each `phase` (`shaping`/`mapping`).
5. On `completed`, call `ingest_epic_result({ taskId })`. It returns:
   - `spec.md` — Application Summary, Modernization Scope, Integration Inventory (`INT-XXX`, 8 signals
     each), NFRs, with a Rally provenance header (FormattedID + ObjectVersion).
   - `epic-signal-ledger.json` — the integration-keyed, span-traced **Brownfield Epic Signal Ledger**.
   - `per_integration_confidence` — fill ratio over the 8 readiness signals (deterministic).
   - `blueprint_gate` — the 8-signal readiness verdict for this spec (`migration_readiness_score`,
     `blocked`, per-integration `findings`, `phase_assignment_preview`, `high_confidence_but_gated`).
     Surface it: an integration with `< 3` integrations or a BLOCK will not pass `blueprint_start`.
6. Write `spec.md` + `epic-signal-ledger.json` to the workspace. The developer reviews `[NEEDS
   CLARIFICATION]` fields and reconciles against the CSA diagram, then runs `/speckit.specify` (CSA
   extraction refines the inventory) → `/speckit.plan` → `/accelerator.blueprint`.

## Notes
- **Format contract (M-1):** ingestion emits the canonical 8-signal migration-readiness template (`spec_parser`/`validate_spec` shape); `/speckit.specify`'s csa-extractor up-converts it to the richer Current-State inventory and reconciles against the CSA diagram.
- Extractive + span-grounded: every signal traces to a verbatim Epic span and a span-grounded value; the
  agent cannot fabricate or alter requirements (e.g. invented volumes/SLAs are dropped).
- Staleness: `/accelerator.refresh` reads the durable `epic-signal-ledger.json` provenance (preferred over
  the editable spec header) and compares Rally's current `ObjectVersion`.
- The brownfield validate_spec gate requires **≥ 3 integrations**; thin Epics will surface CLARIFY markers.
