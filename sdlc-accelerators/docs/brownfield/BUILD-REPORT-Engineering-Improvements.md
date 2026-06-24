# Build Report — Engineering Improvements (1a + #2–#4)

Four engineering improvements identified in self-review, executed. **161 tests passing (+7), 1
skipped, clean lint.**

## #1a — ADK orchestrator steps now REALLY execute (was: facades)
Previously the deterministic ADK steps set placeholder state dicts (e.g. `{"stage":
"map_current_to_target", "deterministic": True}`) without running the tested functions. Now each
step actually runs the corresponding pipeline function, threading inputs/outputs through
`ctx.session.state`:

- **Brownfield** (`orchestrator/adk_steps.py`): MigrationReadinessStep → real `parse_spec` +
  `validate_spec` (halts on BLOCK); SubstitutionStep → real `map_current_to_target`;
  AdrComplianceStep → real `adr_compliance_check`; AssembleContractStep → real `assemble_blueprint`
  (+ CALLS the Eraser MCP tool to render diagram DSLs). Proven by
  `test_brownfield_orchestrator_execution.py` (5 tests): real readiness score, 4 real substitutions,
  a real v2.0 contract with cross-cloud Phase-0, BLOCK halts the chain, and the Eraser tool is
  called per diagram.
- **Greenfield** (`reasoning/adk_steps.py`): ValidateSpecStep → real `validate_spec`;
  AssembleBlueprintStep → real `assemble_blueprint` with the Eraser tool. Proven by
  `test_blueprint_orchestrator_execution.py`.

The steps are driven in tests via a minimal fake InvocationContext (the full InMemoryRunner needs a
live model for the middle LlmAgent, unavailable in CI) — so the deterministic execution is real and
tested; only the live-model leg is mocked.

## #2 — GcsClient de-duplicated (was: byte-identical copies)
The Governance Guardian copy of `gcs_client.py` was byte-for-byte identical to the
solution-accelerator one (divergence risk). It is now a thin re-export from the canonical
`clients/gcs_client.py` — one source of truth, same import path preserved.

## #3 — Shared pattern-search core (was: ~70% duplicated tool files)
The greenfield and brownfield `pattern_search_tool.py` shared the same vertex-wrap + degrade logic.
Extracted into `reasoning/pattern_search_core.py` (`search_patterns_safe`); both tools call it. The
distinct tool signatures (greenfield: ordering signals; brownfield: target/categories/r-factor) are
preserved — only the duplicated wrapping merged.

## #4 — Centralized cross-service path bootstrap (was: ad-hoc sys.path hacks)
- A root `conftest.py` registers every source root once, so **test files no longer carry
  `sys.path.insert`** (removed from all 22 test files).
- A repo-root `_srcpaths.py` (`ensure(*names)`) centralizes the genuinely cross-service path
  reaches (brownfield → solution-accelerator, servers → mcp-auth). The fragile per-file
  dirname-chains in those consumers now call `_srcpaths.ensure(...)`.
- **Accepted, documented convention:** the intra-package inserts (a module adding its OWN `src` so
  sibling top-level packages resolve) remain. Fully removing them requires renaming every package
  and updating every import repo-wide (e.g. `from clients...` → `from solution_accelerator.clients...`)
  — a large, invasive overhaul with poor risk/reward mid-stream. The cross-service smell (the part
  the review named) is addressed; the intra-package convention is a deliberate, documented choice.

## Honest residuals
- The full ADK end-to-end run (InMemoryRunner driving the SequentialAgent through a live Gemini
  call) is still not exercised in CI (no credentials). The deterministic steps' real execution IS
  tested; the live-model leg is mocked.
- The intra-package `sys.path` convention remains by design (see #4).
