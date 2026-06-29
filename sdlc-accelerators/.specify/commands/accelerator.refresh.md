---
command: accelerator.refresh
description: Bidirectional .md <-> .drawio sync through app-blueprint.json.
---

# /accelerator.refresh

When the developer types `/accelerator.refresh`, execute these steps EXACTLY.

## Steps
1. Compare current `app-blueprint.md` and `diagrams/*.drawio.xml` against `.accelerator-hashes` to detect what changed:
   - Case A: only .md changed
   - Case B: only .drawio changed
   - Case C: both changed
2. Call the `refresh` MCP tool with `{ blueprint_md, drawio_files[], spec, plan }`.
3. Apply the returned sync:
   - Case A → regenerate .drawio.xml + .png from the .json topology
   - Case B → update .md §2 narrative + mermaid; regenerate .png
   - Case C → apply auto-merged agreements; present CONFLICTS to the developer to resolve (never silently resolve)
4. Run post-sync validation (parity, adjacency rules, .json consistency). Adjacency: LoopAgent cannot nest in ParallelAgent.
5. Regenerate `app-blueprint.json` and update `.accelerator-hashes`.
6. **Epic drift check (Greenfield, only if the spec was Epic-sourced).** If `spec.md` carries a Rally
   provenance header (FormattedID + ObjectVersion) and `epic-signal-ledger.json` exists in the workspace:
   - Read the stamped `formatted_id` and `object_version` — **prefer `epic-signal-ledger.json`** (the
     durable sidecar; authoritative even if the developer edited away the spec.md provenance header), and
     fall back to the spec header only if the sidecar is absent.
   - Call the **Rally MCP server** (`.vscode/mcp.json`) for that Epic's CURRENT `ObjectVersion`
     (Entra ID SSO — no credentials handled here).
   - If Rally's current ObjectVersion is newer than the stamped one, WARN:
     "⚠️ Rally Epic `<id>` changed since ingestion (ObjectVersion N → M) — the spec may be out of date.
     Re-run `/accelerator.ingest-epic` to re-sync." Do NOT silently overwrite the developer's spec edits.
   - This is a SOURCE-SYSTEM version-token check on the Epic — separate from, and additional to, the
     `.accelerator-hashes` content-hash check above.
7. Tell the developer what changed and surface any conflicts or Epic drift.

## CRITICAL
- `app-blueprint.json` is the reconciliation hub — .md and .drawio sync THROUGH it, never directly to each other.
- The Epic drift check is a WARNING only — it never overwrites the developer's spec. Re-ingestion is the developer's choice.
