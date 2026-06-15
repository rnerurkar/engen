# Build Report — Eraser MCP Diagram Rendering (Option 2)

Diagram rendering moved from a direct Eraser.io headless call to the **Eraser MCP server**
with a two-request async handshake. **71 tests passing, clean lint.**

## The flow
`assemble_blueprint` now:
1. Builds `app-blueprint.md` + `app-blueprint.json` (deterministic, unchanged)
2. Constructs the Eraser DSL from topology (deterministic, unchanged)
3. **Request 1 — submit:** sends each DSL to the Eraser MCP server (`submit_render`), which
   returns a `render_id` and begins rendering
4. **Request 2 — fetch:** retrieves the rendered `.drawio.xml` + `.png` (`fetch_render`)

`assemble_blueprint()` does phase 1 (build + submit); `fetch_rendered_diagrams()` does phase 2
(fetch). Within the async `blueprint_start` pipeline both run server-side, so the IDE receives
fully-rendered diagrams on its `blueprint_result` — i.e. the diagrams come back on the next MCP
request, exactly as specified.

## Components
- `clients/eraser_mcp.py` — `EraserMcpClient` with `submit_render(dsl)` → `{render_id}` and
  `fetch_render(render_id)` → `{drawio_xml, png_base64, status}`. Interface, retry, and result
  contract are real; the MCP SDK transport to the Eraser MCP server is the live seam
  (inject `_submit`/`_fetch` in tests).
- `assembly/assemble.py` — split into `assemble_blueprint` (build + submit) and
  `fetch_rendered_diagrams` (fetch).
- `pipeline/orchestrator.py` — `assemble_from_selections` and `run_deterministic_stages`
  both run the two-phase flow.
- `server/app.py` — `assemble_blueprint_tool` runs both phases; `_ERASER_MCP` injection point added.
- Removed the obsolete `clients/eraser_io.py` (direct-call stub).

## Validations (tested)
- ✅ Two-phase handshake: phase 1 assigns render_ids (artifacts empty), phase 2 fills drawio_xml + png
- ✅ No fabrication: without an Eraser MCP client, `submit_render` raises (does not fake a render)
- ✅ Full pipeline spec.md → selections → assemble (submit+fetch) → rendered diagrams
- ✅ run_deterministic_stages renders both diagrams via the injected Eraser MCP

## Doc updates
The architecture, developer guide, and operations runbook described diagram rendering as
"Eraser.io headless export" (a direct call). All references updated to the **Eraser MCP server**
two-request model: the `assemble_blueprint` tool row, artifact descriptions, the sequence diagram
(participant + submit/fetch steps), the refresh REGENERATE step, auto-regeneration paragraph, the
layered diagram-flow, the runbook health checks + failure modes, and the embedded authored system
prompt (repo copy + dev-guide copy kept in sync).

## Seam
The MCP SDK transport to the Eraser MCP server (`submit_render` / `fetch_render`) — the live
connection. Everything else (DSL construction, handshake orchestration, result handling) is built.
