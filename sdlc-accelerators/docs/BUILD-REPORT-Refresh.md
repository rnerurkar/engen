# Build Report — /accelerator.refresh (bidirectional sync)

Implements the refresh design (architecture lines 1090-1163) per the documented contract.
**51 tests passing (9 new), clean lint.** Built exactly as recommended: deterministic engine
fully implemented; the two prose↔structure bridges are LLM seams (injected, not fabricated).

## The 4-step design, by implementability

| Step | What | Status |
|---|---|---|
| 0. DETECT | SHA compare vs .accelerator-hashes → Case A/B/C/NONE | ✅ fully implemented + tested |
| 1. SYNC | case-dependent reconciliation through app-blueprint.json | ⚙️ deterministic parts done; 2 LLM seams |
| 2. VALIDATE | 5 parity checks (9 sections, node parity, name match, adjacency, json consistency) | ✅ fully implemented + tested |
| 3. REGENERATE | re-derive .json, update hashes (.png via Eraser headless seam) | ✅ implemented + tested |

## Components (services/solution-accelerator/src/refresh/)
- `detect.py` — Step 0: SHA-based change detection + Case A/B/C/NONE + hash read/write
- `drawio_parser.py` — Step 1 (Case B/C): .drawio.xml → topology (deterministic inverse of dsl_builder)
- `reconcile.py` — Step 1 (Case C): diff .md vs .drawio vs last-known .json → AGREE/MD_ONLY/DRAWIO_ONLY/CONFLICT
- `validate_sync.py` — Step 2: all 5 post-sync parity checks → structural_report
- `orchestrator.py` — refresh(): Steps 0→1→2→3, case routing, sync_report/structural_report contract

## Why "fully implement" is not literally possible (by design)
Architecture line 1170: "**LLM is required for prose↔structure bridging.** Unlike the external platform
(machine-parseable STL → fully deterministic sync), SDLC Accelerators's .md uses narrative prose."
So two operations are LLM-only by design and are wired as injected seams:
- `md_to_topology(md, spec, plan)` — Case A/C: prose → structure (extract topology from edited §2 narrative)
- `topology_to_md(json_doc, md)` — Case B/C: structure → prose (regenerate §2 narrative + mermaid)
Tests inject deterministic stand-ins; production wires the Solution Accelerator LLM harness.
**No fabrication:** if a needed seam is absent for the detected case, refresh() raises NotImplementedError.

## Honored ARB findings
- M-1: spec.md/plan.md are read from the workspace automatically — not developer-passed params.
- M-2: the package is §1–§9 (not the old §1-§7 + §8-§12 model).

## Validations (all tested)
- ✅ Case A/B/C/NONE classification
- ✅ drawio.xml parsing (nodes + edges with resolved labels)
- ✅ Conflict detection AND surfacing (never silently resolved — "human in control")
- ✅ Auto-merge on agreement
- ✅ All 5 Step-2 parity checks
- ✅ Full orchestration Case A (with seams), Case NONE, Case C conflict-surfacing
- ✅ No-fabrication: missing LLM seam raises rather than guessing
