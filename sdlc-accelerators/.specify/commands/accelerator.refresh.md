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
6. Tell the developer what changed and surface any conflicts.

## CRITICAL
- `app-blueprint.json` is the reconciliation hub — .md and .drawio sync THROUGH it, never directly to each other.
