# Diagram Sync Status (vs. current design)

Tracks which architecture diagrams reflect the latest design changes (Eraser MCP server,
synchronous render, GCS + AlloyDB blueprint artifact store + findings store, generation gate,
PDF round-trip, Solution Architect group gating).

## ✅ Updated and in sync (text-based — regenerable)
- **Inline mermaid in architecture.md** (2 blocks): the async blueprint sequence and the OAuth
  flow. Now show: Eraser MCP Server, synchronous render, Artifact Store (GCS + AlloyDB pointer)
  on blueprint_result, Solution Architect group gating in JWT validation, the PDF round-trip +
  GCS findings store + verify_generation_gate, and tech-debt JSON to GCS.
- **docs/solution-accelerator-sequence.mmd**: updated to match (was stale — had "Eraser.io
  Headless", direct Task Store result read, old showstopper-only gate). Now mermaid-valid
  (5 block openers / 5 closers).

## ⚠️ STALE — binary images, could NOT be regenerated in this environment
These are PNG/SVG raster/vector exports. Regenerating them needs a headless-Chrome render
(mermaid-cli / draw.io export), which the build environment's network policy blocked (Chrome
download disallowed). They still depict the OLDER design and should be re-exported:
- `docs/solution-accelerator-sequence.png` — re-export from the updated `.mmd` (see command below)
- `docs/SDLC-Accelerators-Architecture-Greenfield.png` / `.svg` — component diagram; may show
  Eraser.io and lack the artifact/findings GCS+AlloyDB stores
- `docs/SDLC-Accelerators-Architecture-Diagram-Detailed.png` / `.svg`
- `docs/SDLC-Accelerators-GA-Architecture-Infographic.png` / `.svg`
- `docs/solution-accelerator-components.png` / `.svg`

## How to regenerate (on a machine with network access)
```bash
npm install -g @mermaid-js/mermaid-cli
npx puppeteer browsers install chrome-headless-shell
mmdc -i docs/solution-accelerator-sequence.mmd -o docs/solution-accelerator-sequence.png -b white
mmdc -i docs/solution-accelerator-sequence.mmd -o docs/solution-accelerator-sequence.svg -b white
```
For the component/infographic PNGs (not mermaid-sourced), update the source (draw.io / design
tool) to add: Eraser MCP Server (replacing Eraser.io headless), the Blueprint Artifact Store and
Findings Store (GCS + AlloyDB pointer), and the Solution Architect group gate, then re-export.
