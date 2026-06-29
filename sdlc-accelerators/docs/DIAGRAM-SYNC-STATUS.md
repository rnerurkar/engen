# Diagram Sync Status (vs. current design)

## ✅ Epic-to-Spec redesign — brownfield front-door diagrams regenerated (SVG authored + PNG re-rendered via cairosvg @2x)
The brownfield archetype's front door changed from `/accelerator.ingest-epic` (partial pre-fill, then
`/speckit.specify` up-convert) to **`/accelerator.epic-to-spec`** — a deterministic fusion of the Rally
Epic (Modernization Scope: per-component Refactor/Rehost + AWS target) with the upstream CSA
`architecture.md`, emitting the final `spec.md` directly. These diagrams now reflect that flow:
- `brownfield-10-step-flow.svg/png` — Step 0 (CSA Agent + BA/SA Epic) → Step 1 `/accelerator.epic-to-spec` (front door) → Step 2 `/speckit.specify` (no-Epic fallback); downstream unchanged.
- `brownfield-steps-4-7-internals.svg/png` — BAND 3 rewritten to the 3 deterministic fusion phases (resolve & cross-walk → compose → gate & trace); `create_epic_signal_ledger` relabeled legacy-fallback; IP boundary updated.
- `sdlc-accelerators-brownfield-architecture.svg/png` + `_detailed.svg/png` — front door relabeled epic-to-spec (Epic × CSA fusion); CSA Agent now emits diagram + architecture.md.
- `reference-case-csa.svg/png` — CSA components tagged with stable `CSA-COMP-xxx` IDs (the join key).
- `reference-case-tsa.svg/png` — per-component disposition badges (CSA-COMP-001 · Refactor, 002/003 · Rehost).

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
