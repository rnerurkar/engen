# Greenfield sample — FNOL claims intake (Epic-sourced)

Demonstrates the **optional Greenfield front door**: `/accelerator.ingest-epic` turns a **Rally Epic**
into a signal-bearing `spec.md`, so the developer **reviews** rather than authors. See Architecture
§ "Epic-to-Spec Ingestion (Greenfield)", Developer Guide § 2.3a, Operations Runbook § 9a.

## What's here
| File | Role |
|---|---|
| `epic.md` | Human-readable Rally Epic **E4417** (the source of requirements). |
| `epic.json` | The structured Epic payload the coding agent fetches via the **Rally MCP server** (content only — no credentials). |
| `spec.md` | **Generated** by `ingest_epic` (Phase A agentic shaping → Phase B deterministic mapping). Carries a Rally provenance header (FormattedID + ObjectVersion) and per-section confidence. |
| `epic-signal-ledger.json` | The section-keyed, span-traced **Epic Signal Ledger** (Phase A output). Every signal traces to a verbatim Epic span; provenance/reference artifact — do not hand-edit. |
| `transcripts/ingest-epic.md` | The IDE transcript of the `/accelerator.ingest-epic` run. |
| `plan.md` | **Generated** by `/plan` after the spec is reviewed (technical plan: infra, model, CI/CD, security). |
| `app-blueprint.md` / `app-blueprint.json` | **Generated** by the Solution Accelerator Agent's `recommend_architecture` FunctionTool via `/accelerator.blueprint` — demonstrating the full **Epic → spec → blueprint** path (Sequential[classify→Parallel-enrich→route]+HITL). |
| `transcripts/blueprint.md` | The IDE transcript of `/accelerator.blueprint` (names the agent + `recommend_architecture`). |

## The flow this sample shows
1. `/accelerator.ingest-epic` → coding agent interviews for the Rally **FormattedID** (`E4417`),
   calls the **Rally MCP server** (`.vscode/mcp.json`, Entra ID SSO) for the Epic, then calls
   `ingest_epic` on the Solution Accelerator with the Epic **content only**.
2. **Phase A — agentic shaping:** the one LlmAgent extracts span-traced signals into the Epic Signal
   Ledger (it cannot invent — any signal whose span is not verbatim in the Epic is dropped).
3. **Phase B — deterministic mapping:** renders the 10-section `spec.md`, computes per-section
   confidence from the signal-slot **fill ratio**, and stamps Rally provenance.
4. Developer reviews low-confidence sections (here **§3**, **§6**, **§8** carry
   `[NEEDS CLARIFICATION]`), confirms via `/specify`, then `/plan` → `/accelerator.blueprint` as usual.

## Per-section confidence (fill ratio, deterministic)
§1 1.00 · §2 1.00 · §3 0.33 · §4 1.00 · §5 1.00 · §6 0.00 · §7 1.00 · §8 0.00 · §9 1.00 · §10 1.00

## Staleness
`spec.md` stamps Rally **ObjectVersion 14**. On `/accelerator.refresh`, if Rally's current ObjectVersion
is newer, the developer is warned the Epic drifted and offered a re-ingest (a source-version-token check,
distinct from the `.accelerator-hashes` content check).
