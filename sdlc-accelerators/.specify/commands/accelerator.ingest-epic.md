---
command: accelerator.ingest-epic
description: Ingest a Rally Epic and convert it into a signal-bearing spec.md (optional Greenfield front door).
---

# /accelerator.ingest-epic

You are the coding agent. When the developer types `/accelerator.ingest-epic`, execute these steps EXACTLY.
This is the OPTIONAL Greenfield front door: it turns a Rally Epic into a signal-bearing `spec.md` so the
developer reviews rather than authors. The downstream flow (`/specify` review → `/plan` →
`/accelerator.blueprint`) is unchanged.

Reference: Architecture § "Epic-to-Spec Ingestion (Greenfield)" + Appendix § G2; Developer Guide § 2.3a;
Operations Runbook § 9a.

## Preconditions
- The **Rally MCP server** must be registered in `.vscode/mcp.json` (see `.specify/templates/mcp.json`).
  If it is not available, tell the developer to add it (Operations Runbook § 9a) and STOP.
- Rally auth is the developer's **Entra ID SSO inside the IDE**. NEVER request, store, or forward Rally
  credentials — the Rally MCP server handles auth. The Solution Accelerator receives epic CONTENT only.

## Steps
1. Confirm the Rally MCP server is reachable (declared in `.vscode/mcp.json`). If not, STOP per Preconditions.
2. **Capability-negotiated interview.** Read the Rally MCP server's available queries, then ask the developer
   ONLY for what you cannot derive — at minimum the Rally Epic **FormattedID** (e.g. `E1234`); project/workspace
   only if ambiguous.
3. Call the **Rally MCP server** to fetch the Epic: description, acceptance criteria, NFRs, linked
   features/stories, dependencies, plus Rally `ObjectVersion` and `LastUpdateDate`.
4. Call the Solution Accelerator MCP tool `ingest_epic_start` with `{ epic: <fetched epic payload> }`
   (epic CONTENT only — NOT credentials). It returns `{ taskId, pollInterval }` in < 2s.
5. Poll `ingest_epic_status({ taskId })` every `pollInterval` seconds. Report each `phase` to the developer
   in the chat pane: "Shaping epic signals…" (Phase A) → "Mapping to spec.md…" (Phase B).
6. When `status == "completed"`, call `ingest_epic_result({ taskId })`. It returns
   `{ spec_md, epic_signal_ledger, per_section_confidence }`.
7. Write to the workspace:
   - `spec.md` — signal-bearing, 10 sections, with a Rally provenance header (FormattedID + ObjectVersion).
   - `blueprint_gate` — the Step-0 `validate_spec` verdict for this spec: `{ quality_score, blocked, findings[], high_confidence_but_gated[] }`. Surface it so the developer sees real blueprint-readiness, not fill-ratio confidence alone. If `blocked` is true, point them at the gated sections during `/specify` review.
   - `epic-signal-ledger.json` — the section-keyed signal ledger (reference/provenance artifact; do NOT edit).
8. Report per-section confidence. Tell the developer to review **low-confidence sections** and any
   `[NEEDS CLARIFICATION]` markers, then run `/specify` to confirm (quick — structure is already populated),
   then `/plan` and `/accelerator.blueprint`.

## Error handling
- Rally MCP server not registered → instruct the developer to add `.vscode/mcp.json` and STOP.
- Epic not found / FormattedID invalid → ask the developer to re-enter the FormattedID.
- `ingest_epic_status` returns `failed` with an empty-ledger reason → the Epic has no description/ACs to
  shape; ask the BA to flesh out the Epic, or fall back to `/specify`.
- 401 from the Solution Accelerator → OAuth token expired; re-authenticate (silent refresh) and retry.

## CRITICAL
- NEVER request, store, or forward Rally credentials — the Rally MCP server handles auth inside the IDE.
- NEVER edit `epic-signal-ledger.json` by hand — it is a provenance/reference artifact.
- NEVER invent Epic content. If a signal is absent in the Epic, leave it for `/specify` review; the
  server-side shaping agent is extractive and cannot fabricate requirements.
- The coding agent has NO direct access to the Solution Accelerator's reasoning or system prompt — both
  shaping (Phase A) and mapping (Phase B) run server-side; you only orchestrate Rally → the `ingest_epic_*` tools.
- Rally MCP read-tool names (e.g. `get_epic`, `query_epics`, `get_acceptance_criteria`) are environment-specific — discover them from the registered Rally MCP server rather than assuming.
