# Brownfield Diagram Sync Status

Tracks the brownfield architecture diagrams against the implemented code and the reconciled
inline mermaid. Produced as part of the P2 (diagram sync) remediation.

## ✅ In sync (done)
- **`.mmd` source of truth created:** `docs/csa-tsa-blueprint-sequence.mmd` — the async
  blueprint_start/status/result sequence, now the editable source for the inline mermaid in
  `csa-tsa-architecture.md` §9.3 (parallels greenfield's `solution-accelerator-sequence.mmd`).
- **Inline mermaid reconciled:** the §9.3 sequence block matches the `.mmd` source and the
  implemented flow — `validate_spec` gate, the four tools, `recommend_architecture` (LLM),
  `assemble_blueprint`, the **Design Contract Store (GCS + AlloyDB pointer)** (now built in P1),
  and the **Eraser MCP Server** as the renderer.
- **Renderer references corrected:** the three "Draw.io headless service" *renderer* references in
  the architecture prose are now "Eraser MCP server," matching the actual platform decision.
  NOTE: `.drawio.xml` editable files + the Draw.io VSCode extension references are intentionally
  RETAINED — the platform decision is "Eraser MCP renders → `.drawio.xml` + `.png`; developers edit
  the `.drawio.xml` in the Draw.io extension." Draw.io the *format/editor* is correct; only Draw.io
  as the *renderer* was the inconsistency.

## 🔴 Needs regeneration on a headless-render host (cannot be done in this sandbox)
The binary raster/vector exports must be regenerated wherever Chrome headless is available
(`mmdc` is installed here, but no Chrome binary, so rendering fails at browser launch):

| File | Regenerate from | Command |
|---|---|---|
| `docs/csa-tsa-blueprint-sequence.png` | `docs/csa-tsa-blueprint-sequence.mmd` | `mmdc -i docs/csa-tsa-blueprint-sequence.mmd -o docs/csa-tsa-blueprint-sequence.png` |
| `docs/sdlc-accelerators-brownfield-architecture.{png,svg}` | the architecture source diagram | re-export from the diagram tool / mermaid source |
| `docs/sdlc-accelerators-brownfield-architecture_detailed.{png,svg}` | detailed architecture source | re-export |
| `docs/reference-case-csa.{png,svg}` | reference-case CSA source | re-export |
| `docs/reference-case-tsa.{png,svg}` | reference-case TSA source | re-export |

**Why flagged, not done:** rendering requires a browser engine (puppeteer/chrome-headless-shell)
that is not present in this build environment. The `.mmd` source is committed so regeneration is a
one-command step on any host with Chrome headless (e.g. CI with `npx @mermaid-js/mermaid-cli`).

## Verification after regeneration
1. `mmdc -i docs/csa-tsa-blueprint-sequence.mmd -o docs/csa-tsa-blueprint-sequence.png`
2. Confirm the rendered PNG shows: validate_spec gate, the four tools, Eraser MCP Server,
   Design Contract Store, and the start/status/result lifecycle.
3. Re-export the architecture and reference-case diagrams from their sources and confirm no
   "Draw.io headless" renderer label remains.

---

## Update — ADK orchestrator design change (sequence diagrams refined)

The opt-in ADK orchestrator + pattern-search FunctionTool changed the *internal execution* of the
blueprint pipeline. Sync assessment:

- **Sequence diagrams (refined):** the 2 `.mmd` sources (`csa-tsa-blueprint-sequence.mmd`,
  `solution-accelerator-sequence.mmd`) and their 2 inline mermaid mirrors now note the OPT-IN
  orchestrator path and show retrieval as a FunctionTool call (`search_transition_patterns` /
  `search_architecture_patterns`). The default path (BG runs the tools directly) is unchanged and
  still depicted.
- **Architecture / component / reference-case PNGs (NOT changed):** the orchestrator is internal to
  the Background Job and is OPT-IN (off by default); it adds no component and changes no
  developer/operator action, so it is not visible at these diagrams' abstraction level. (They also
  require a headless renderer to regenerate — see above.)
- **The `.mmd` blueprint-sequence PNG** would only need regeneration if you want the refined notes
  rendered to raster; the `.mmd` source is the source of truth and is current.
