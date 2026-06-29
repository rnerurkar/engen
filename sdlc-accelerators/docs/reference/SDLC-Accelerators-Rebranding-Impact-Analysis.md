# Rebranding Impact Analysis

## AgentCatalyst → SDLC Accelerators

| Old Term | New Term |
|---|---|
| AgentCatalyst | SDLC Accelerators |
| Blueprint Advisor | Solution Accelerator |
| Blueprint Advisor MCP Server | Solution Accelerator MCP Server |
| /catalyst.blueprint | /accelerator.blueprint |
| /catalyst.refresh | /accelerator.refresh |
| /catalyst.assess | /accelerator.assess |
| /catalyst.generate | /accelerator.generate |
| Governance Guardian | **NO CHANGE** (keep as-is) |

---

## Decisions Required Before Executing

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | MCP tool names (blueprint_start, blueprint_status, blueprint_result, assemble_blueprint) | A: Rename to accelerator_start, etc. B: Keep as blueprint_* | **B: Keep.** These are internal API names — renaming breaks protocol compatibility. "Blueprint" describes what the tool produces, not the product name. |
| 2 | Artifact names (app-blueprint.md, app-blueprint.json) | A: Rename to app-accelerator.md. B: Keep as app-blueprint.* | **B: Keep.** "Blueprint" is the artifact type (like "report" or "spec"). Changing the filename forces changes in every code reference, Jinja template, and JSON schema. |
| 3 | validate_composition tool name | A: Rename. B: Keep | **B: Keep.** Internal API name. |
| 4 | .blueprint-hashes file | A: Rename to .accelerator-hashes. B: Keep | **A: Rename.** This is a workspace file the developer sees. |

---

## Impact Summary

| Category | Files Impacted | Total Text Replacements |
|---|---|---|
| Core MD documents (3) | 3 | ~456 |
| CSA-TSA MD documents (3) | 3 | ~219 |
| Mermaid sequence diagram (1) | 1 | ~17 |
| FNOL DSL examples (1) | 1 | ~4 |
| Diagrams — PNG (must regenerate) | 7 | N/A (visual) |
| Diagrams — SVG (text editable) | 2 | ~20 |
| ELT Decks — PPTX | 2 | ~50+ slides |
| Patent application | 2 | ~30 |
| ARB reports | 2 | ~15 |
| IP analysis docs | 2 | ~40 |
| **File renames** | **8** | N/A |
| **Total** | **26 files** | **~850+ replacements** |

---

## Detailed Impact by File

### Tier 1: Core Documentation (highest impact)

#### 1. Architecture Doc (`agentcatalyst-architecture-archetype-agnostic.md`)

| Pattern | Count | Examples |
|---|---|---|
| AgentCatalyst | 35 | Title, headers, narrative, footnotes, comparisons |
| Blueprint Advisor | 85 | MCP Server name, section headers, narratives, tool descriptions, security section, capacity section |
| /catalyst.* | 65 | /catalyst.blueprint, /catalyst.refresh, /catalyst.assess, /catalyst.generate throughout |
| catalyst- | 13 | catalyst-cli, catalyst-specific references |
| Inline mermaid "Blueprint Advisor" | ~10 | Participant labels in 2 mermaid sequence diagrams |
| Inline mermaid "/catalyst." | ~12 | Commands in sequence flows |
| **Total replacements** | **~220** | |

**Filename rename:** `agentcatalyst-architecture-archetype-agnostic.md` → `sdlc-accelerators-architecture-archetype-agnostic.md`

#### 2. Developer Guide (`agentcatalyst-archetype-agnostic-developer-guide.md`)

| Pattern | Count | Examples |
|---|---|---|
| AgentCatalyst | 19 | Title, intro, workflow descriptions, FAQ |
| Blueprint Advisor | 79 | MCP Server references, tool descriptions, walkthrough narratives |
| /catalyst.* | 86 | All 4 commands throughout walkthroughs, examples, CLI output blocks |
| catalyst- | 19 | catalyst-cli, catalyst-specific code examples |
| **Total replacements** | **~203** | |

**Filename rename:** `agentcatalyst-archetype-agnostic-developer-guide.md` → `sdlc-accelerators-archetype-agnostic-developer-guide.md`

#### 3. Operations Runbook (`agentcatalyst-operations-greenfield_runbook.md`)

| Pattern | Count | Examples |
|---|---|---|
| AgentCatalyst | 7 | Title, architecture context, footer |
| Blueprint Advisor | 34 | MCP Server health checks, monitoring, troubleshooting |
| /catalyst.* | 33 | Command references in operational procedures |
| catalyst- | 12 | catalyst-specific operational references |
| **Total replacements** | **~86** | |

**Filename rename:** `agentcatalyst-operations-greenfield_runbook.md` → `sdlc-accelerators-operations-greenfield_runbook.md`

---

### Tier 2: CSA-TSA Documentation (brownfield/strangler-fig variants)

#### 4. CSA-TSA Architecture (`csa-tsa-speckit-architecture.md`)

| Pattern | Count |
|---|---|
| AgentCatalyst | 28 |
| Blueprint Advisor | 37 |
| /catalyst.* | 41 |
| **Total** | **~106** |

#### 5. CSA-TSA Developer Guide (`csa-tsa-speckit-developerguide.md`)

| Pattern | Count |
|---|---|
| AgentCatalyst | 6 |
| Blueprint Advisor | 15 |
| /catalyst.* | 37 |
| **Total** | **~58** |

#### 6. CSA-TSA Operating Playbook (`csa-tsa-speckit-operating-playbook.md`)

| Pattern | Count |
|---|---|
| AgentCatalyst | 9 |
| Blueprint Advisor | 27 |
| /catalyst.* | 16 |
| **Total** | **~52** |

---

### Tier 3: Supporting Documents

#### 7. Sequence Diagram (`blueprint-advisor-sequence.mmd`)

| Pattern | Count | Location |
|---|---|---|
| Blueprint Advisor | 2 | Participant label, title comment |
| /catalyst.* | 9 | Phase labels, command references |
| **Total** | **~11** | |

**Filename rename:** `blueprint-advisor-sequence.mmd` → `solution-accelerator-sequence.mmd`

#### 8. FNOL Eraser DSL Examples (`FNOL-Eraser-DSL-Examples.md`)

| Pattern | Count | Location |
|---|---|---|
| Blueprint Advisor | 4 | Pipeline description, source references |
| **Total** | **~4** | |

#### 9. Refresh Sync Flow Diagram (`refresh-sync-flow.png`)

| What needs to change | Current | New |
|---|---|---|
| Title | "/catalyst.refresh — Bidirectional Sync Flow" | "/accelerator.refresh — Bidirectional Sync Flow" |
| Footer | "AgentCatalyst — Bidirectional Refresh Sync..." | "SDLC Accelerators — Bidirectional Refresh Sync..." |

**Must regenerate PNG from updated SVG.**

---

### Tier 4: Diagrams (PNG — must regenerate from scratch)

These are rasterized images with embedded text. Text cannot be edited — the diagrams must be regenerated.

| # | Diagram | Old Text to Replace |
|---|---|---|
| 1 | `AgentCatalyst-Architecture-Diagram-Detailed.png` | "AgentCatalyst" in title, "Blueprint Advisor MCP Server" in box labels, "/catalyst.*" in command labels |
| 2 | `AgentCatalyst-Architecture-Diagram-Detailed.svg` | Same (SVG is text-editable) |
| 3 | `AgentCatalyst-GA-Architecture-Infographic.png` | "AgentCatalyst" throughout |
| 4 | `AgentCatalyst-GA-Architecture-Infographic.svg` | Same (SVG editable) |
| 5 | `blueprint-advisor-components.png` | "Blueprint Advisor" in all labels |
| 6 | `blueprint-advisor-components.svg` | Same (SVG editable) |
| 7 | `agentcatalyst-brownfield-architecture_detailed.png` | "AgentCatalyst" in title + labels |
| 8 | `refresh-sync-flow.png` | "/catalyst.refresh" in title, "AgentCatalyst" in footer |

**Note:** SVG files (items 2, 4, 6) can be text-edited with sed. PNG files must be regenerated from their SVG sources.

**Filename renames for diagrams:**
- `AgentCatalyst-Architecture-Diagram-Detailed.*` → `SDLC-Accelerators-Architecture-Diagram-Detailed.*`
- `AgentCatalyst-GA-Architecture-Infographic.*` → `SDLC-Accelerators-GA-Architecture-Infographic.*`
- `blueprint-advisor-components.*` → `solution-accelerator-components.*`
- `agentcatalyst-brownfield-architecture_detailed.*` → `sdlc-accelerators-brownfield-architecture_detailed.*`

---

### Tier 5: Deliverables (ELT Decks, Patents, ARB Reports, IP Analysis)

| # | File | AgentCatalyst refs | Blueprint Advisor refs |
|---|---|---|---|
| 1 | `AgentCatalyst-ELT-5-Slide-Updated.pptx` | ~20 (title, headers, every slide) | ~10 |
| 2 | `AgentCatalyst-ELT-15-Slide-Updated.pptx` | ~40 (title, headers, every slide) | ~20 |
| 3 | `AgentCatalyst-Provisional-Patent-v1.md` | ~15 | ~10 |
| 4 | `AgentCatalyst-Provisional-Patent-v1.docx` | ~15 | ~10 |
| 5 | `AgentCatalyst-ARB-PartII-Migration-Report.md` | ~10 | ~5 |
| 6 | `AgentCatalyst-ARB-Bidirectional-Refresh-Review.md` | ~5 | ~5 |
| 7 | `the external platform-vs-AgentCatalyst-IP-Analysis.md` | ~30 | ~10 |
| 8 | `the external platform-vs-AgentCatalyst-IP-Separation.md` | ~20 | ~10 |

**Filename renames:** All 8 files need "AgentCatalyst" → "SDLC-Accelerators" in filename.

**Patent implications:** The patent was filed using "AgentCatalyst" terminology. If the rebrand happens before formal filing, update the patent. If after filing, the patent uses the old name — add a note that "AgentCatalyst" is the original development name for what is now marketed as "SDLC Accelerators."

---

## What Does NOT Change

| Item | Why it stays |
|---|---|
| **Governance Guardian** | Already branded and approved — user confirmed keep as-is |
| **app-blueprint.md / .json** | Artifact type name, not product name (like "report.docx") |
| **blueprint_start / status / result** | Internal MCP tool API names — renaming breaks protocol |
| **assemble_blueprint** | Internal tool name |
| **validate_composition** | Internal tool name |
| **recordTechDebt** | Governance Guardian tool — not part of this rebrand |
| **spec.md / plan.md** | Input artifact names — platform-agnostic |

---

## Execution Approach (Recommended)

| Phase | Scope | Effort | Risk |
|---|---|---|---|
| **Phase 1** | 3 core MD docs + sequence diagram + refresh-sync SVG/PNG | ~2 hours | Low — sed replacements + SVG text edit + PNG regeneration |
| **Phase 2** | 3 CSA-TSA MD docs | ~1 hour | Low — same sed patterns |
| **Phase 3** | 7 diagram PNG/SVG files | ~3 hours | Medium — must regenerate PNGs from SVGs or recreate |
| **Phase 4** | 2 ELT PowerPoint decks | ~2 hours | Medium — PPTX text replacement requires python-pptx |
| **Phase 5** | 2 patent docs + 2 ARB reports + 2 IP analysis docs | ~1 hour | Low — sed replacements |
| **Phase 6** | File renames (8 files) + cross-reference updates | ~1 hour | Medium — every document that references a renamed file needs updating |
| **Total** | **26 files** | **~10 hours** | |

---

*Impact Analysis — Not for External Distribution*
