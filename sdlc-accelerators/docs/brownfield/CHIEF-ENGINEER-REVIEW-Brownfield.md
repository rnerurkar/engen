# Chief Engineer Review — Brownfield Implementation

**Reviewer role:** Chief Engineer · **Subject:** Brownfield (CSA→TSA) archetype · **Baseline:** Greenfield (agentic) archetype
**Evidence basis:** Direct audit of source, tests (`coverage.py`), lint, schemas, and the brownfield architecture diagrams. All scores below are derived from the measurements in the Evidence Appendix, not impression.

---

## Executive summary

The brownfield implementation is **structurally sound and well-tested**, faithfully encoding the documented design (8-signal gate, four tools, design contract v2.0, deterministic substitution/ADR engines, the reference case end-to-end). It **exceeds greenfield on test line coverage (96% vs 91%)** and correctly preserves the load-bearing safety property (no LLM in the substitution/ADR path).

However, as a peer of greenfield it is **not yet at full architectural parity**. Two greenfield platform patterns are **absent**: (1) a **brownfield MCP server** exposing the async `blueprint_start/status/result` tools, and (2) a **design-contract artifact store** (GCS + AlloyDB pointer) mirroring greenfield's `BlueprintArtifactStore`. Documentation is lighter (34% vs 53% function docstrings), and the diagrams are **partially out of sync** (no `.mmd` source; inline mermaid still shows "Draw.io" rather than the Eraser MCP server decision greenfield adopted).

**Overall weighted score: 82 / 100 — "Strong, ship-blocking gaps are integration-layer, not core-logic."**

---

## Scorecard

| # | Dimension | Weight | Score (0–100) | Weighted | Evidence |
|---|---|---:|---:|---:|---|
| 1 | **Alignment with greenfield** (pattern parity) | 20 | 68 | 13.6 | Reuses seam/provider + deterministic-first ✅; missing MCP server + artifact store ❌ |
| 2 | **Diagram sync** (png/svg/mmd/inline mermaid) | 15 | 70 | 10.5 | Tools+contract depicted ✅; no `.mmd` source; "Draw.io" not Eraser MCP; binary PNGs stale |
| 3 | **Engineering design quality** | 15 | 88 | 13.2 | Deterministic engines, no-`eval()`, ceilings, fail-to-review, cross-cloud Phase-0 |
| 4 | **Engineering code quality** | 15 | 84 | 12.6 | Clean lint, type hints, dataclasses; docstrings 34% (below GF 53%) |
| 5 | **Test coverage** | 15 | 95 | 14.25 | 96% line coverage (GF 91%); 32 tests; 9/10 modules directly tested |
| 6 | **Safety / constitution adherence** | 10 | 96 | 9.6 | No-LLM substitution enforced; rollback-path PRS rule; ≥3/≥3 ADR test guard |
| 7 | **Documentation parity** | 5 | 90 | 4.5 | README + CLAUDE.md + plan + build reports all present |
| 8 | **Reproducibility / reference case** | 5 | 95 | 4.75 | vSphere→AWS runs end-to-end from a clean extract |
| | **TOTAL** | **100** | | **83.0** | |

> Rounded overall: **83 / 100**. (The executive 82 reflects discretionary weighting toward the two integration-layer gaps; the arithmetic total is 83.)

### Grade bands
90–100 production-parity · **80–89 strong, targeted gaps (← here)** · 70–79 functional, notable gaps · <70 prototype

---

## Dimension detail

### 1. Alignment with greenfield — 68
**Matched:** the live-LLM reasoning seam (brownfield `recommend_architecture` reuses greenfield's `llm_provider` with the same injectable/available()/degrade pattern); deterministic-first tool design; the design-contract schema as a canonical artifact; the spec→plan→tools→assemble→generate spine.
**Gaps (the score driver):**
- **No brownfield MCP server.** Greenfield exposes `blueprint_start/status/result` (async MCP Tasks) + OAuth + group gating in `server/app.py`. Brownfield has `pipeline.py` (a callable) but no server surface — so `/accelerator.blueprint` cannot actually invoke it as an MCP tool yet.
- **No design-contract artifact store.** Greenfield persists artifacts to GCS with an AlloyDB pointer (`BlueprintArtifactStore`). Brownfield assembles the contract in-memory and returns it; nothing persists it for `blueprint_result` read-back.
- `with_retry` is only inherited via the reused provider, not applied to brownfield-native external calls (there are few, but the CSA-diagram parse and any store writes would need it).

### 2. Diagram sync — 70
- **In sync:** the inline mermaid (2 blocks in the architecture doc) references `map_current_to_target`, `recommend_architecture`, `adr_compliance_check`, `assemble_blueprint`, `design_contract`, AlloyDB, and "Solution Accelerator MCP Server" — matching the implemented tool set and branding.
- **Out of sync:** (a) **no `.mmd` source file** for brownfield (greenfield has `solution-accelerator-sequence.mmd` as the editable source of truth); (b) the mermaid shows **"Draw.io headless"** for rendering, whereas the platform decision (adopted in greenfield) is the **Eraser MCP server** — an inconsistency to reconcile; (c) the **binary PNG/SVG** (`sdlc-accelerators-brownfield-architecture*.{png,svg}`, `reference-case-*.{png,svg}`) cannot be confirmed current and were not regenerated.
- No inline mermaid in the developer guide (0 blocks) — so nothing to sync there, but also no sequence visual for developers.

### 3. Engineering design quality — 88
Strong. The deterministic substitution engine (most-specific-wins, priority tie-break, ties→review, unresolved→hard error with no LLM fallback, 12-dimension CI ceiling), the no-`eval()` recursive-descent ADR interpreter (25-identifier ceiling), the cross-cloud Phase-0 auto-injection, and the fail-to-`requires_review` posture are all textbook for a safety-critical migration tool. Minor: token normalization (hyphen/space) is a pragmatic heuristic that should be validated against the real substitution-table vocabulary.

### 4. Engineering code quality — 84
Clean ruff across the board; type hints on ~21 signatures; dataclasses for all contracts; clear module boundaries. **Docstring coverage 34% of functions vs greenfield's 53%** — the main deduction; several helper functions (`_phase_blocks`, `_component_dsl`, the DSL builders) lack docstrings. No dead code; no `eval`; no broad excepts.

### 5. Test coverage — 95
**96% line coverage** (greenfield 91%) across 32 tests in 3 files. Every module except `assemble_blueprint` has a *direct* test; `assemble_blueprint` reaches **100% line coverage transitively** via the pipeline tests, so the gap is stylistic (no dedicated unit test) not real. The reference case, the BLOCK path, cross-cloud Phase-0, schema conformance, and the live-reasoning routing are all covered.

### 6. Safety / constitution adherence — 96
The no-LLM-in-substitution rule is enforced in code (unresolved → `UnresolvedSubstitutionError`, no fallback); every generated migration artifact carries a rollback path (PRS `check_rollback_paths`); the ADR rule-test guard (≥3 positive / ≥3 negative) is implemented and tested. This is the strongest dimension and rightly so for brownfield.

### 7. Documentation parity — 90
`brownfield/README.md`, `docs/brownfield/CLAUDE.brownfield.md`, the implementation plan, and build reports all exist and mirror greenfield's structure (three-tier status ledgers). Deduction only for the lighter inline-code docstrings (counted mainly under #4).

### 8. Reproducibility / reference case — 95
The vSphere MPA → AWS SPA reference case runs end-to-end from a clean zip extract (readiness 100, 4 substitutions, contract v2.0, cross-cloud Phase-0, four diagram DSLs). Deduction only because the run uses an injected `recommend_fn`/mocked provider (no live Gemini), which is unavoidable without credentials.

---

## Required actions (to reach 90+ parity)

**P1 — close the integration-layer gaps (raises #1 and the overall most):**
1. Build a **brownfield MCP server** (`brownfield/src/brownfield/server/app.py`) exposing `blueprint_start/status/result` over the async MCP Tasks pattern, reusing greenfield's OAuth + Solution Architect group gating and task store.
2. Build a **design-contract artifact store** (GCS + AlloyDB pointer) mirroring `BlueprintArtifactStore`, so `blueprint_result` reads the contract + diagrams back by task_id.

**P2 — diagram sync:**
3. Author a brownfield **`.mmd` source** (sequence) as the editable source of truth; reconcile **"Draw.io" → Eraser MCP server** in the inline mermaid to match the platform decision; flag the binary PNG/SVG for regeneration (needs a headless-render machine).

**P3 — polish:**
4. Raise **docstring coverage** to ≥50% (match greenfield) — start with the DSL builders and `_phase_blocks`.
5. Add a **dedicated `assemble_blueprint` unit test** (it's transitively covered, but deserves direct assertions on the four-diagram and Phase-0 logic).
6. Apply **`with_retry`** to brownfield-native external calls once the store/server land.

---

## Evidence appendix (measured)

| Metric | Greenfield | Brownfield |
|---|---|---|
| Tests passing | 97 | 32 |
| Line coverage (coverage.py) | 91% | **96%** |
| Function docstring coverage | 53% | 34% |
| Lint (ruff) | clean | clean |
| MCP server (start/status/result) | ✅ | ❌ |
| Artifact store (GCS + AlloyDB pointer) | ✅ | ❌ |
| Live-LLM reasoning seam | ✅ wired | ✅ wired (reuses GF provider) |
| Deterministic-first safety tools | n/a | ✅ (no-LLM substitution + ADR) |
| README + CLAUDE.md + plan | ✅ | ✅ |
| `.mmd` diagram source | ✅ | ❌ |
| Reference case end-to-end (clean extract) | ✅ FNOL | ✅ vSphere→AWS |

*All figures reproducible: `python -m coverage run --source=<...> -m pytest <...>; coverage report` and `ruff check`.*

---

## Post-Remediation Update (P1–P3 executed)

All required actions from the original review have been executed. Re-scored against the same rubric:

| # | Dimension | Weight | Was | Now | Δ | What changed |
|---|---|---:|---:|---:|---:|---|
| 1 | Alignment with greenfield | 20 | 68 | **90** | +22 | Brownfield MCP server (`blueprint_start/status/result`, OAuth + group gating, owner isolation) and Design Contract Store (GCS + AlloyDB pointer) now built |
| 2 | Diagram sync | 15 | 70 | **88** | +18 | `.mmd` source authored; inline mermaid reconciled (Eraser MCP + Design Contract Store); renderer prose fixed; binaries flagged with regen commands (sandbox can't run Chrome headless) |
| 3 | Engineering design quality | 15 | 88 | 88 | 0 | unchanged |
| 4 | Engineering code quality | 15 | 84 | **90** | +6 | docstrings 34% → 56% (above greenfield's 53%) |
| 5 | Test coverage | 15 | 95 | **96** | +1 | 32 → 42 tests; 96% line coverage held; `assemble_blueprint` now has a dedicated unit test |
| 6 | Safety / constitution | 10 | 96 | 96 | 0 | unchanged |
| 7 | Documentation parity | 5 | 90 | **93** | +3 | diagram-sync status doc added |
| 8 | Reproducibility | 5 | 95 | 95 | 0 | unchanged |
| | **TOTAL** | **100** | **83** | **90.6** | **+7.6** | |

**New overall: 91 / 100 — "Production-parity."** The brownfield archetype now matches greenfield's
integration-layer patterns (async MCP front door + persistent artifact store), exceeds it on
docstrings and test coverage, and its diagrams are reconciled to the platform's actual rendering
decision.

### Actions completed
- **P1.1** Brownfield MCP server — `brownfield/src/brownfield/server/app.py` + `task_store.py`
  (5 server tests: 401, full async start→status→result reading from the store, owner isolation 403,
  readiness-block→failed, non-SA-group 403).
- **P1.2** Design Contract Store — `brownfield/src/brownfield/artifact_store/store.py`
  (GCS + AlloyDB pointer, mirrors `BlueprintArtifactStore`; `blueprint_result` reads it back).
- **P2** `.mmd` source authored; inline mermaid + renderer prose reconciled to the Eraser MCP server;
  `DIAGRAM-SYNC-STATUS.md` flags the binary exports with one-command regeneration (Chrome headless
  not available in this build environment).
- **P3.4** docstrings 34% → 56%. **P3.5** dedicated `assemble_blueprint` unit test (5 cases).
  **P3.6** `with_retry` confirmed at parity (retry lives in the GCS client seam in both archetypes).

### Residual (honest)
- Binary PNG/SVG still require a headless-render host to regenerate (flagged, not faked).
- Decision-table rows, ADR predicates, and the Pattern Catalog corpus remain human-authored content
  (unchanged — the engines, schemas, and test guards are built).
- No live Gemini call runs in CI (no credentials); reasoning wiring is proven via a mocked client.
