# Build Report — Blueprint Artifact Store + Synchronous Eraser Render

Synchronous Eraser MCP rendering + durable artifact storage (GCS + AlloyDB pointer),
mirroring the Governance Guardian findings pattern. **77 tests passing, clean lint.**

## 1. Eraser MCP rendering is now synchronous
`EraserMcpClient.render(dsl) -> {drawio_xml, png_base64}` in one call (the Eraser MCP server
renders synchronously). Removed the two-request submit/fetch split. `assemble_blueprint`
renders both diagrams inline. MCP transport remains the live seam (inject `_render` in tests).

## 2. Blueprint artifact store (GCS + AlloyDB pointer)
`artifact_store/store.py` — `BlueprintArtifactStore`:
- `write_blueprint(task_id, owner_id, markdown, json_doc, diagrams)` writes ALL artifacts to GCS
  under `gs://<bucket>/blueprints/<owner_id>/<task_id>/`:
  `app-blueprint.md`, `app-blueprint.json`, `diagrams/<name>.drawio.xml`, `diagrams/<name>.png`
  (PNGs stored as decoded bytes — object storage, NOT base64-in-DB), and records ONE pointer
  row in AlloyDB (`task_id`, `owner_id`, `gcs_prefix`, manifest).
- `read_pointer(task_id)` / `read_blueprint(task_id)` read the pointer and fetch artifacts back,
  returning md + json inline + diagrams (base64) combined for the IDE.
GCS put/get are injectable seams; pointer model, key scheme, manifest, and reference backing are real.

## 3. Server wiring (solution-accelerator/server/app.py)
- `blueprint_start`: after the pipeline completes, **persists all artifacts to the store**
  (GCS + AlloyDB pointer). The async task record holds only lightweight status — not megabytes
  of base64.
- `blueprint_result`: reads the AlloyDB pointer by task_id (owner_id-isolated), fetches artifacts
  from GCS, and returns **md + json + diagrams combined** to the IDE.

## 4. Governance Guardian gate — AlloyDB → GCS findings lookup (made explicit)
`verify_generation_gate` already looked up the findings pointer in AlloyDB and read findings.md
from GCS. Strengthened: it now uses the GCS get seam explicitly and returns `findings_gcs_uri`
(the URL it resolved via the pointer) alongside the stop/resume signal — so the coding agent sees
the gate consulted the stored findings. Critical/High → stop (resolve + /accelerator.refresh);
only Medium/Low → write tech-debt JSON + resume.

## Validations (tested)
- ✅ Store: pointer + manifest; read-back combines md + json + diagrams; PNG round-trips base64;
  GCS put seam receives all 6 objects; PNG stored as raw bytes not base64
- ✅ Synchronous Eraser render in assemble_blueprint
- ✅ E2E: blueprint_start persists → blueprint_result reads md+json+diagrams from the store
- ✅ E2E: GG gate looks up AlloyDB pointer → GCS findings URL → critical/high → stop, returns findings_gcs_uri

## Doc updates
architecture / developer-guide / operations-runbook: Eraser render is synchronous (sequence
diagram, tool rows, refresh steps, system prompt); added the Blueprint Artifact Store design
(GCS + AlloyDB pointer) and a blueprint_result troubleshooting row.

## Seams
- Eraser MCP transport (`render`)
- GCS put/get for blueprint artifacts + findings
- AlloyDB-backed pointer tables (blueprint + findings) with Row-Level Security
