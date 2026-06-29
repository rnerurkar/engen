# ARB Review — Epic → Spec → Design Blueprint via the Solution Accelerator Agent

**Reviewer role:** Chief Architect / Engineer (ARB)
**Scope:** The Epic-to-Spec front door (`/accelerator.ingest-epic`, `ingest_epic_*`, Phase A shaping → Phase B mapping, Epic Signal Ledger) and its hand-off into the design blueprint, with emphasis on the newly introduced **Solution Accelerator Agent** (one ADK agent, two FunctionTools).
**Artifacts reviewed:** `services/solution-accelerator/src/{agent,ingest,server,reasoning}`, `schemas/`, `.specify/{commands,templates,preset.yml}`, `samples/greenfield/fnol-claims-intake/`, `docs/{architecture,developer-guide,operations-runbook}.md`, and the greenfield diagrams.
**Method:** Code read + executed probes (schema validation, extractive-guarantee adversarial input, `validate_spec` on the generated spec). Findings cite file/evidence.

## Summary

| Severity | Count | Theme |
|---|---:|---|
| Critical | 1 | The "cannot invent" extractive guarantee is not actually enforced |
| High | 3 | Agent is built-but-never-run; ADK modeling soundness; ingest-confidence vs spec-gate misalignment |
| Medium | 5 | Staleness is prompt-only; doc tool-count drift; sample stops at spec.md; epic prompt-injection surface; non-standard `mcp.json` keys |
| Low | 4 | Phase polling not observable; cosmetic confidence; naming shorthand; unverified preset/Rally assumptions |

**Verdict:** *Conditional pass.* The two-phase design (non-deterministic extractive shaping → deterministic mapping) is sound and the IP-boundary reasoning is well-constructed. But the **Critical** finding undercuts the central claim of the reviewed scope and must be fixed before the design is presented as "extractive / cannot invent," and the three **High** findings should be resolved before the Solution Accelerator Agent is described as load-bearing.

---

## CRITICAL

### C-1 — The extractive "cannot invent" guarantee constrains the *span*, not the *value* it renders into the spec
**Evidence.** `ingest/shaping.py::validate_ledger` keeps a signal iff `_norm(span) in epic_corpus`. The signal's `value` (the text Phase B actually writes into `spec.md` via `mapping.py::_render_section`, which renders `s.value`, not `s.epic_span`) is never checked against the span. Adversarial probe (real span, fabricated value) is **accepted**:

```
input : value="P99 latency under 1 millisecond (fabricated)", epic_span="within 5 minutes at the 95th percentile"
result: KEPT  → rendered into spec.md §10
```

**Impact.** The headline guarantee asserted throughout the artifacts — Architecture ("the agent literally cannot invent requirements"), the shaping prompt, the diagram IP panel, the patent-boundary note — is **overstated**. A model (or a prompt-injected Epic) can attach an arbitrary requirement to any verbatim Epic snippet and it flows into the spec with full provenance. Because this is the exact mechanism the patent claims rest on, it is a claim-integrity defect, not a cosmetic one.

**Recommendation.** Enforce value↔span fidelity, e.g. (a) render the **verbatim span** (or a span-derived value) into the spec rather than the free-text `value`; or (b) add a validator check that `value` is entailed by/derived from `span` (token-overlap threshold, or a deterministic transform); or (c) keep `value` for readability but persist and display the `epic_span` as the authoritative text and gate on it. Update the wording to "span-grounded" if full entailment is not enforced.

---

## HIGH

### H-1 — The Solution Accelerator Agent is constructed and discarded; the delegation is never actually exercised
**Evidence.** `agent/solution_accelerator_agent.py::delegate()` calls `build_solution_accelerator_agent()` and ignores the returned agent, then calls `TOOL_FNS[capability]` directly. The ADK `LlmAgent` object is therefore **built and thrown away on every call**; no code path runs it (no ADK Runner invocation anywhere). The internals diagram further labels `invoke_llm_agent` as "runs the ADK agent," but `invoke_llm_agent` calls the Gemini provider directly (`reasoning/llm_provider.invoke`), not the agent.
**Impact.** The central design statement — "the MCP server delegates to the Solution Accelerator Agent" — is **cosmetic in the reference implementation**. Reviewers/auditors verifying the claim against the code will find the agent inert. Diagram label is inaccurate.
**Recommendation.** Either (a) make `delegate()` actually run the agent (ADK Runner / `agent.run`) so the seam is real, or (b) be explicit that the agent is a *logical grouping* of two prompt-bound reasoning functions and that runtime dispatch is direct — and correct the diagram label to "invokes the model (Gemini)" rather than "runs the ADK agent."

### H-2 — ADK modeling soundness: an `LlmAgent` whose two FunctionTools each perform LLM reasoning
**Evidence.** `recommend_architecture` and `create_epic_signal_ledger` are registered as `FunctionTool`s but each internally calls `invoke_llm_agent` (an LLM). In ADK, an `LlmAgent` uses its own model to *decide which tool to call*; tools are normally deterministic.
**Impact.** Run faithfully via the ADK Runner, this incurs **two model invocations per request** (the agent's routing LLM + the tool's reasoning LLM) and makes tool selection non-deterministic — even though the server already knows which capability it wants. Run as in the reference (bypassing the Runner, per H-1) the agent is inert. Either way the "agent + 2 LLM-FunctionTools" shape is awkward.
**Recommendation.** Prefer one of: (a) two prompt-bound reasoning **functions** invoked directly by the server (what the code effectively does) — describe the "agent" as a logical unit; or (b) a genuine ADK agent whose FunctionTools are **deterministic** (retrieval, validation) with the *agent's own* model doing the reasoning; or (c) two separate single-purpose agents. Avoid the LLM-routing-an-LLM-tool double call.

### H-3 — Ingest confidence (fill-ratio) is not contracted with the Step-0 `validate_spec` gate
**Evidence.** Phase B confidence = `filled/expected_slots` (`epic_models.py`). The blueprint Step-0 gate (`reasoning/validate_spec.py`) instead greps the **rendered spec text** for ordering words (§2), a measurable regex (§10), and own-system flags (§5). Nothing guarantees the two agree. The sample passes (`quality_score 100`) only because the shaping `value` strings happen to contain "first/then/in parallel" and "< 5 / > 95% / 100%".
**Impact.** A high-confidence ingested spec (e.g. §2 fill-ratio 1.0) can still **WARN/BLOCK** at `/accelerator.blueprint` if the normalized values omit the literal trigger tokens — a confusing "the agent said 100% but blueprint rejected it" developer experience. This is squarely in the Epic→spec→blueprint path under review.
**Recommendation.** Align the contracts: have Phase B render values that preserve the tokens `validate_spec` keys on (or compute ingest confidence using the *same* extractor `validate_spec` uses), and add a test asserting "any non-empty-section ingested spec passes `validate_spec`."

---

## MEDIUM

### M-1 — Epic ObjectVersion staleness is prompt-only; no code, no enforcement, no test
**Evidence.** The drift check lives only in `.specify/commands/accelerator.refresh.md` (step 6). `services/solution-accelerator/src/refresh/` contains **no** `object_version`/epic handling. It also depends on the provenance header surviving developer edits to `spec.md`, which nothing enforces.
**Impact.** A documented, diagrammed feature with zero implementing/verifying code; silently degrades if the header is edited away.
**Recommendation.** Add a small server-side or library helper that extracts the stamped ObjectVersion and compares it (testable), and/or store provenance outside the editable spec body (e.g. `.accelerator-epic` sidecar) so edits can't erase it.

### M-2 — Tool-count drift in the operations runbook
**Evidence.** `operations-runbook.md` line 38 ("exposes **six** MCP tools …") and line 506 ("MCP Server with **5** tools") / line 508 ("three fast tools plus two deterministic tools") omit `ingest_epic_start/status/result`. `architecture.md` already lists all nine.
**Impact.** Accuracy/completeness: ops readers get an out-of-date tool inventory for the very capability under review.
**Recommendation.** Update the runbook counts/lists to include the three `ingest_epic_*` tools (and the health-check/versioning notes for the epic-shaping prompt).

### M-3 — The greenfield epic sample stops at `spec.md` (no plan/blueprint)
**Evidence.** `samples/greenfield/fnol-claims-intake/` contains `epic.*`, `spec.md`, `epic-signal-ledger.json` — **no** `plan.md`, `app-blueprint.md/.json`.
**Impact.** The sample evidences Epic→spec but **not** spec→design-blueprint via the agent's `recommend_architecture` tool — i.e. it does not demonstrate the full reviewed path end-to-end.
**Recommendation.** Extend the sample with `plan.md` + a generated `app-blueprint.md/.json` (even stubbed via the existing pipeline test harness) and an `ingest→blueprint` transcript, to prove the ingested spec actually produces a valid blueprint.

### M-4 — Epic content is an unbounded prompt-injection / DoS surface
**Evidence.** `ingest_epic_start(epic: dict)` accepts arbitrary epic text that is concatenated into the shaping prompt (`shaping.build_shaping_message`). No size cap, no sanitation.
**Impact.** A crafted Epic could attempt to steer Phase A. *Partially mitigated* by the extractive span check + deterministic Phase B — but note C-1 weakens that mitigation (injected text that appears verbatim could be lifted as a value).
**Recommendation.** Cap epic size, strip/escape instruction-like content, and (with C-1 fixed) rely on span-grounding. Add an adversarial-epic test.

### M-5 — `mcp.json` template uses non-standard keys
**Evidence.** `.specify/templates/mcp.json` includes `"//"` and `"//auth"` documentation keys.
**Impact.** VS Code's `mcp.json` schema / strict parsers may reject unknown top-level keys, breaking Rally MCP registration for some users.
**Recommendation.** Move the prose into a sibling `mcp.README.md`; keep the JSON to the schema VS Code expects.

---

## LOW

- **L-1 — Async phases not observable.** `ingest_epic_start` runs `run_ingest` synchronously, so `ingest_epic_status` can never return an intermediate `phase: shaping/mapping` (only terminal states). Consistent with `blueprint_start`'s reference behavior, but the schema/diagram imply observability. Note it, or make the job truly async.
- **L-2 — Cosmetic confidence string.** Over-filled sections render `confidence 1.00 (filled 4/3)` (`mapping._render_section`). Clamp the displayed `filled` to `expected_slots` or show `4 (≥3)`.
- **L-3 — Naming shorthand.** "ingest_epic" is used as a collective shorthand alongside the real `ingest_epic_start/status/result` in the command/diagrams; standardize.
- **L-4 — Unverified external assumptions.** The `preset.yml` `mcp:` template key and the Rally MCP tool names (`get_epic`, `query_epics`, `get_acceptance_criteria`) are assumed; verify against the actual spec-kit preset schema and the deployed Rally MCP server.

---

## What is sound (for balance)
- The **two-phase split** (non-deterministic extractive shaping → fully deterministic mapping) is the right shape and cleanly separates the model's job from reproducible spec generation.
- **Phase B is genuinely deterministic** and stamps provenance; the ledger **validates against its JSON Schema**; tenant isolation (`owner_id`) is enforced on `ingest_epic_status/result`.
- The **IP-boundary reasoning** (section-keyed ledger, fill-ratio confidence, ObjectVersion token, assess-gate finding; not claiming the shared agent/tool structure) is coherent and well-documented.
- **Reuse of one reasoning unit** for both capabilities is the right instinct for the non-overlap argument; H-1/H-2 are about *how* it is modeled, not *whether* to reuse.

## Suggested disposition
- **Before "extractive/cannot-invent" is claimed anywhere:** fix **C-1**.
- **Before the Solution Accelerator Agent is presented as load-bearing:** resolve **H-1, H-2**; align **H-3**.
- **Next iteration:** M-1…M-5.
- *(Not legal advice — patent-claim implications of C-1/H-1/H-2 should be confirmed with a practitioner.)*

---

## Resolution log — all findings fixed (follow-up pass)

All findings below were remediated and verified (`tests/test_ingest_epic.py` passes incl. new cases; sample regenerated; ledger schema-valid; C-1 adversarial probe now drops the fabricated value).

| ID | Status | Fix (evidence) |
|---|---|---|
| **C-1** | ✅ Resolved | `shaping._value_grounded()` now gates the **value** against its span: every number in `value` must appear in `span` + lexical overlap required. Adversarial probe ("P99 < 1ms" on a "5 minutes" span) is dropped. Wording changed to "span-grounded; cannot fabricate/alter requirements" in architecture/dev-guide/runbook, the shaping prompt, code docstrings, and the diagram. New test `test_c1_*`. |
| **H-1** | ✅ Resolved | `SolutionAcceleratorAgent.run()` added; `delegate()` now builds the agent and **runs it** (no discard). Live `LlmAgent` bound into `adk_agent`; `_run_via_adk_runner` seam. Diagram label "runs the ADK agent" → "invokes the model (Gemini)". |
| **H-2** | ✅ Resolved | Dispatch documented + implemented as **direct capability dispatch** (server names the tool; no LLM tool-router → no second/non-deterministic model call). Noted in agent docstring + architecture §steps 4–7. |
| **H-3** | ✅ Resolved | `run_ingest` now runs `validate_spec` on the produced spec and returns `blueprint_gate {quality_score, blocked, findings, high_confidence_but_gated}`. Added to `ingest_epic_result` schema + the command prompt. New test `test_h3_*` (sample passes, no hidden gating). |
| **M-1** | ✅ Resolved | New `ingest/staleness.py` (`read_provenance` preferring the durable ledger sidecar; `is_stale`). Refresh command reads the ledger sidecar (authoritative) before the editable header. New test `test_m1_*`. |
| **M-2** | ✅ Resolved | Operations-runbook tool counts corrected to **9** (adds `ingest_epic_start/status/result`). |
| **M-3** | ✅ Resolved | FNOL sample now includes `plan.md`, `app-blueprint.md`, `app-blueprint.json`, `transcripts/blueprint.md` — demonstrating Epic → spec → **blueprint** via the agent's `recommend_architecture` tool. |
| **M-4** | ✅ Resolved | `MAX_EPIC_CHARS` cap in `run_ingest` (clear `epic_too_large` error); span-grounding (C-1) is the primary injection mitigation. New test `test_m4_*`. |
| **M-5** | ✅ Resolved | `mcp.json` reduced to the schema keys (`servers`, `inputs`); prose moved to `mcp.README.md`. |
| **L-1** | ✅ Resolved | Synchronous phase-reporting documented in `run_ingest` docstring + the ingest result/status contract. |
| **L-2** | ✅ Resolved | Over-filled sections now render `filled 3+/3` (clamped) in `mapping._render_section`. |
| **L-3** | ✅ Resolved | Command/diagram standardized on `ingest_epic_*`. |
| **L-4** | ✅ Resolved | `preset.yml` + command carry an explicit "verify per environment" note for the `mcp:` key and Rally tool names. |

**Updated verdict:** *Pass.* The Critical and all High findings are remediated and covered by tests; the central claim is now precise ("extractive + span-grounded") and enforced, and the Solution Accelerator Agent is genuinely executed via direct dispatch. *(Patent-claim wording for C-1/H-1/H-2 still merits a practitioner's confirmation.)*
