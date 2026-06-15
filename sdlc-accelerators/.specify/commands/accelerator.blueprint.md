---
command: accelerator.blueprint
description: Call the Solution Accelerator MCP Server to produce the app-blueprint package.
---

# /accelerator.blueprint

You are the coding agent. When the developer types `/accelerator.blueprint`, execute these steps EXACTLY.

## Preconditions
- `spec.md` and `plan.md` must exist in the workspace. If either is missing, tell the developer to run `/specify` and `/plan` first, then STOP.

## Steps
1. Read `spec.md` and `plan.md` from the workspace.
2. Authenticate to the Solution Accelerator MCP Server (OAuth 2.1 + Entra ID). On first use, open the browser SSO flow; afterward use the cached token (silent refresh).
3. Call the MCP tool `blueprint_start` with `{ spec: <spec.md contents>, plan: <plan.md contents> }`. It returns `{ taskId, pollInterval }` in < 2s.
4. Poll `blueprint_status({ taskId })` every `pollInterval` seconds. Report each `stage` to the developer in the chat pane ("Searching pattern catalog...", "Discovering A2A agents...", "Reasoning about architecture...", "Assembling blueprint...").
5. When `status == "completed"`, call `blueprint_result({ taskId })`. It returns `{ markdown, json, diagrams[] }`.
6. Write to the workspace:
   - `app-blueprint.md` (PRIMARY — the developer edits this)
   - `app-blueprint.json` (DERIVED — never edit directly)
   - `diagrams/*.drawio.xml` and `diagrams/*.png` (decode base64)
   - update `.accelerator-hashes`
7. Tell the developer: blueprint ready, review `app-blueprint.md` (all 9 sections editable), then run `/accelerator.assess`.

## CRITICAL
- NEVER fabricate blueprint content. If the MCP call fails, report the error and STOP — do not generate a blueprint yourself.
- The coding agent has NO direct access to Vertex AI Search or the system prompt — all intelligence is server-side.
