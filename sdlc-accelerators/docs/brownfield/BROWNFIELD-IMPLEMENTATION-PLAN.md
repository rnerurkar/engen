# Brownfield (CSA→TSA) — Comprehensive Implementation Plan

A step-by-step plan to build the brownfield archetype on the existing SDLC Accelerators platform.
Grounded in `docs/csa-tsa-architecture.md`, `docs/csa-tsa-developer-guide.md`, and
`docs/csa-tsa-operating-playbook.md`. The brownfield archetype converts a Current-State
Architecture (CSA) into a Target-State Architecture (TSA) — wholly or selectively — driven by a
per-integration **scope** (in `spec.md`) and **R-factor** (in `plan.md`).

The plan reuses the platform spine already built for greenfield (async MCP front door, OAuth +
group gating, GCS + AlloyDB stores, generation gate, refresh, Eraser MCP rendering, the live-service
seam pattern). Brownfield is additive: four migration tools, a deterministic substitution engine, an
ADR predicate interpreter, a design-contract v2.0, brownfield templates/skill, and the reference case.

---

## Guiding principles (carry through every phase)

1. **Safety over completeness.** Brownfield touches a running production system. Every phase has a
   rollback path; coexistence (dual-read/dual-write/cutover) is first-class, not an afterthought.
2. **Deterministic substitution, never LLM.** `map_current_to_target` and `adr_compliance_check`
   are rules engines. Only `recommend_architecture` pattern selection uses an LLM.
3. **Reuse the spine.** Do not re-implement auth, async tasks, GCS/AlloyDB stores, the generation
   gate, or refresh. Brownfield plugs into them.
4. **Author vs. scaffold.** Build engines, schemas, and tests; the decision-table rows, ADR rule
   predicates, and the recommend_architecture prompt are human-authored (EA / platform eng).
5. **Reference case is the fixture.** vSphere MPA → AWS SPA is brownfield's FNOL. If a module can't
   process it end-to-end, it isn't done.

---

## Phase 0 — Foundations: schemas, templates, CLAUDE.md, reference-case skeleton

**Goal:** establish the contracts and fixtures everything else is tested against.

- 0.1 **Author `docs/brownfield/CLAUDE.brownfield.md`** (DONE — companion to this plan). It is the
  per-archetype generation context: the four tools, the 8-signal gate, R-factor vocabulary, the
  no-LLM-in-substitution rule, protected identifiers, and the IP boundary.
- 0.2 **Schemas (`schemas/`):**
  - `design-contract.schema.json` (v2.0) — lifecycle, `tech_substitutions[]`, `pattern_selections[]`,
    `attested_adrs[]`, `migration_phases[]`, `staleness_triggers`, `cutover_strategy`.
  - `tech-substitution-row.schema.json` — one decision-table row: `source_tokens[]`, `r_factor`,
    context dimensions (≤12), `target_tokens[]`, `adr_ref`, `transition_pattern_ref`, `priority`, `confidence`.
  - `adr-rule.schema.json` — one ADR predicate: key `(source_tech, target_tech, functional_category, r_factor)`,
    predicate expression, action (`PASS|FLAG|REJECT`), `adr_id`, test cases (≥3 pos, ≥3 neg).
  - `blueprint_request.schema.json` — the spec+plan envelope for `blueprint_start`.
- 0.3 **Templates:**
  - `templates/spec/spec-template.brownfield.md` — Application Summary, Modernization Scope (which
    integrations to convert), Integration Inventory (one block per INT-XXX with the 8-signal fields),
    NFRs. (Mirror Developer Guide §7.)
  - `templates/plan/plan-template.brownfield.md` — per-integration R-factor, cutover strategy,
    sequencing/phase, coexistence window. (Mirror Developer Guide §9.)
- 0.4 **Reference-case skeleton** `examples/vsphere-mpa-aws-spa/`: `inputs/csa-diagram.*`,
  `inputs/spec.md`, `inputs/plan.md`, and placeholder `outputs/` to be filled as tools come online.
- 0.5 **Register the archetype:** add `brownfield-migration` to the archetype→renderer map (engine.py)
  and the `.specify` preset so `/speckit.specify` can select it.

**Exit criteria:** schemas validate; templates render; reference-case inputs parse; `CLAUDE.brownfield.md`
in place. Tests: schema-validation unit tests + a fixture-load test for the reference case.

---

## Phase 1 — Spec capture + the 8-signal migration-readiness gate (two layers)

**Goal:** turn a CSA diagram + developer input into a validated `spec.md`, and gate it.

- 1.1 **CSA diagram parsing (`csa-extractor`):** nodes→components, edges→integrations, group
  containers→cloud/on-prem boundaries, edge labels→protocol hints. Pre-fill integration blocks.
  (The CSA Agent that PRODUCES the diagram is an upstream external dependency — out of scope; we only
  PARSE its output. Support the documented diagram formats per Architecture §7.4.)
- 1.2 **`validate_spec` — 8-signal gate (server-side, Step 0 of `blueprint_start`):** CSA Completeness,
  Integration Type, Data Flow Direction, Criticality Rating, Coexistence Constraints, API Surface,
  State Management, Data Volume + SLA. Each → PASS/WARN/BLOCK. Output `migration_readiness_score` (0–100)
  + `phase_assignment_preview` (Phase 1 read / Phase 2 write / Phase 3 decommission). Any BLOCK →
  `blueprint_start` returns immediately with specific guidance.
- 1.3 **Local layer (SpecKit preset):** the same checks run during `/speckit.specify` capture so the
  developer fixes gaps before server submission. Two-layer design is deliberate (brownfield errors hit
  production).
- 1.4 Wire `validate_spec` as the brownfield Step 0 (parallels greenfield's `validate_spec`, different
  signal set).

**Exit criteria:** the reference-case spec passes; a deliberately-incomplete spec BLOCKs with the right
signal. Tests: per-signal PASS/WARN/BLOCK matrix; phase-assignment preview; reference-case spec → score.

---

## Phase 2 — Two-stage R-factor plan (Plan Gate)

**Goal:** capture and govern the R-factor + cutover decisions per integration.

- 2.1 **`/speckit.plan.draft`:** first-pass `plan.md` — R-factor (rehost/replatform/refactor/rearchitect/
  retire), cutover strategy, sequencing per integration, derived from the spec's signals.
- 2.2 **`/speckit.plan.review`:** publish for async EA/LOB review; structured comments; resolve →
  `reviewed` state. Acceptance telemetry: solo-drafted vs reviewed. (This IS the Plan Gate — no new gate.)
- 2.3 **Plan parsing** into the envelope consumed by `map_current_to_target` (R-factor + context per INT).

**Exit criteria:** reference-case plan drafts + reviews to `reviewed`; R-factor vocabulary validated
(reject synonyms). Tests: plan parse → per-integration R-factor + context; review-state transitions.

---

## Phase 3 — Tool 1: `map_current_to_target` (deterministic substitution engine)

**Goal:** map each in-scope integration CSA→TSA via the context-filtered decision table. **No LLM.**

- 3.1 **Context-filtered rules engine:** `lookup(source_tech, r_factor, {criticality, data_size_class,
  compliance_regime, messaging_pattern, region_constraints, partner_constraints, ...})`. ≤12 context
  dimensions (CI-enforced ceiling). Most-specific matching row wins; priority field breaks specificity
  ties; remaining ties → `requires_review`.
- 3.2 **Output:** `tech_substitutions[]` (integration_id, source_tokens, r_factor, context_matched,
  target_tokens, adr_ref, transition_pattern_ref, confidence) + `unresolved[]`.
- 3.3 **Failure mode:** no matching `(source_token, r_factor, context)` → integration into `unresolved[]`
  and the tool returns an error. **No LLM fallback** — forces unknowns to the platform-eng review queue.
- 3.4 **Decision-table store:** rows in AlloyDB (reuse the AlloyDB client seam); authoring UI is an
  operations concern (Playbook §5) — build the engine + schema + row-loader, not the UI.

**Exit criteria:** reference-case substitutions reproduce (e.g. IBM MQ 9.1 + refactor → AWS SQS,
PAT-T-007 dual-publish); an unmatched tuple errors to `unresolved[]`. Tests: most-specific-wins,
priority tie-break, ceiling enforcement, unresolved path, ≥3 pos/≥3 neg per sample row.

---

## Phase 4 — Tool 2: `recommend_architecture` (the one LLM stage) + `validate_composition`

**Goal:** select a migration pattern per integration via RAG, then validate the composition.

- 4.1 **Per-integration retrieval:** query vector from intent paragraph + `functional_category[]` +
  `target_tech`; hybrid-search the Pattern Catalog (Vertex AI Search — reuse the vertex_search seam);
  filter candidates by `r_factor_supports[]` + `functional_category[]` overlap.
- 4.2 **LlmAgent selection:** pick a winner from top-K; confidence = score gap to runner-up;
  confidence < 0.65 → `requires_review: true`. (Reuse the Gemini/ADK llm_harness seam + authored prompt.)
- 4.3 **Tool discovery:** applicable tools from the Tool Registry (Apigee API Hub — reuse apigee seam).
- 4.4 **`validate_composition(pattern_tree)` (deterministic):** catch Strangler-fig wrapping big-bang
  cutover (invalid), LoopAgent containing HITL (preserved greenfield rule), dual-publish without
  downstream idempotency (cross-check vs plan). Unresolved review flags block generation downstream.

**Exit criteria:** reference-case selections produced; low-confidence → review flag; the three
composition violations are caught. Tests: retrieval filter, confidence gate, each composition rule
(positive + negative), graceful degradation when the corpus/live calls aren't wired.

---

## Phase 5 — Tool 3: `adr_compliance_check` (deterministic predicate DSL interpreter)

**Goal:** enforce ADR policy per (integration, target_tech, pattern). **No `eval()`.**

- 5.1 **ADR Constraint Store query** by key `(source_tech, target_tech, functional_category, r_factor)`;
  returns applicable ADRs with structured predicates.
- 5.2 **Predicate DSL interpreter** (~200 lines, parser-combinator, no `eval()`): evaluate expressions
  like `target_tech == 'aurora-mysql' AND data_size_gb > 10000 → REJECT (ADR-118)`. Governance:
  ≤25 identifiers (CI-enforced), ≥3 positive + ≥3 negative tests per rule, conflict detection.
- 5.3 **Output per integration:** `pass` (+`attested_adrs[]` — the audit trail) / `flag`
  (`requires_review`) / `reject` (violated ADR). `attested_adrs[]` flows into the design contract.

**Exit criteria:** reference-case ADRs attested; a violating tuple REJECTs with the right ADR; the
identifier ceiling and mandatory-tests checks run in CI. Tests: interpreter (each operator), ceiling
enforcement, contradiction detection, ≥3/≥3 per sample rule, attested-ADR audit-trail shape.

---

## Phase 6 — Tool 4: `assemble_blueprint` + design contract v2.0 + four diagrams

**Goal:** deterministically assemble the TSA blueprint, contract, and diagrams.

- 6.1 **`app-blueprint.md`:** one block per integration — target pattern, tech substitution, IaC module
  refs (IaC Module Registry / GitHub seam), attested ADRs.
- 6.2 **Four diagrams** (via the Eraser MCP server — reuse the synchronous render + artifact store):
  Component (end-state TSA), Sequence (end-state runtime), **Sequence (transition** — dual-write windows,
  strangler routes, cutover gates), Infrastructure (AWS account/VPC/region/cross-cloud links).
- 6.3 **Cross-cloud Phase-0:** when a selected pattern uses cross-cloud topology (PrivateLink/PSC/Direct
  Connect), inject a Phase-0 entry in `migration_phases[]` with an external-team coordination checklist.
- 6.4 **Design contract v2.0:** emit `lifecycle: LIVE` with `staleness_triggers` (version stamps for ADR
  store, substitution table, IaC manifest). Persist via the **blueprint artifact store** (GCS + AlloyDB
  pointer) already built — md/json/diagrams to GCS, one pointer in AlloyDB.

**Exit criteria:** reference-case blueprint + contract + four diagrams assemble; cross-cloud Phase-0
appears when applicable; contract validates against design-contract.schema.json v2.0. Tests: block-per-
integration assembly, four-diagram generation, Phase-0 injection, contract schema conformance, artifact-
store round-trip.

---

## Phase 7 — Governance assessment + generation gate (reuse greenfield spine)

**Goal:** assess the brownfield blueprint and gate generation — reuse what's built.

- 7.1 **`/accelerator.assess`** (Governance Guardian): the PDF round-trip (md→PDF→Eraser MCP assess→
  findings PDF→MD Critical/High/Medium/Low) already exists; ensure the brownfield blueprint's
  integration blocks extract cleanly. The EA rubric content is human-authored.
- 7.2 **`verify_generation_gate`** (already built): findings.md → GCS + AlloyDB pointer; block on
  Critical/High with resolve + `/accelerator.refresh` + reassess; only Medium/Low → tech-debt JSON to GCS.
  Brownfield adds: also block if any integration has an unresolved `requires_review` (from Tools 1/2/3)
  or an `unresolved[]` substitution.

**Exit criteria:** a brownfield blueprint with a critical finding OR an unresolved substitution blocks;
a clean one resumes with tech-debt recorded. Tests: gate blocks on unresolved review flag; PDF round-trip
on a brownfield blueprint.

---

## Phase 8 — Brownfield-aware generation (skill + templates)

**Goal:** generate born-safe migration code.

- 8.1 **`skills/domain-skills/brownfield-migration.SKILL.md`** + `templates/code/brownfield-migration/`:
  Strangler-Fig proxy, message bridge, dual-write window, cutover gate, decommission job. Each artifact
  emits a rollback path and the coexistence/cutover telemetry the transition diagram references.
- 8.2 **Per-integration generation** keyed on R-factor + selected pattern: sync→Strangler proxy,
  async→message bridge, batch→scheduled job, bidirectional→dual-write window (hardest, Phase 2).
- 8.3 **Required artifacts** (reuse pre-commit + inner-loop eval): emit `.pre-commit-config.yaml` +
  `tests/eval_inner_loop.py`; brownfield adds migration-safety checks (rollback present, telemetry wired).
- 8.4 **PRS scanner** extension: brownfield constitution rules (every migration artifact has a rollback
  path; no hard-cutover on a bidirectional integration without dual-write; coexistence telemetry present).

**Exit criteria:** reference-case generates per-integration migration code with rollback + telemetry;
PRS scanner flags a missing rollback path. Tests: generator per R-factor, rollback-presence check,
byte-identical golden tree for the reference case.

---

## Phase 9 — Design contract lifecycle + `/accelerator.refresh` (brownfield)

**Goal:** keep the contract alive across long-lived migrations.

- 9.1 **Lifecycle states** (DRAFT→LIVE→STALE→REFRESHED) and **staleness detection** against
  `staleness_triggers` (ADR store / substitution table / IaC manifest version stamps).
- 9.2 **`/accelerator.refresh`** (reuse the bidirectional sync engine): re-validate that
  `app-blueprint.md` ↔ the four diagrams ↔ `design_contract.json` are in sync; surface conflicts, never
  silently resolve. Re-run substitution/ADR checks if a trigger version changed.
- 9.3 **Long-lived project handling:** partial re-runs when only some integrations change phase.

**Exit criteria:** a bumped trigger version marks the contract STALE; refresh re-syncs and re-attests.
Tests: staleness detection per trigger, refresh re-sync, partial re-run.

---

## Phase 10 — Reference case end-to-end + docs + diagram sync

**Goal:** prove the whole archetype and document it.

- 10.1 **Reference case end-to-end:** vSphere MPA → AWS SPA from CSA diagram → spec → plan(review) →
  4 tools → blueprint + contract + 4 diagrams → assess → gate → generate → migration code. This is the
  brownfield integration test.
- 10.2 **Docs:** ensure `csa-tsa-architecture.md`, `csa-tsa-developer-guide.md`,
  `csa-tsa-operating-playbook.md` match what was built; sync the brownfield diagrams (inline mermaid +
  `.mmd`; the binary PNG/SVG need a headless-render machine — note in a diagram-sync status).
- 10.3 **README:** add a brownfield section + an implementation-status tier for it (mirroring the
  greenfield ✅/⚙️/🔴 ledger).

**Exit criteria:** reference case runs end-to-end (with live-service seams injected); docs in sync.

---

## What to REUSE vs. BUILD (so brownfield doesn't re-implement the spine)

| Reuse as-is (already built + tested) | Build new for brownfield |
|---|---|
| Async front door: `blueprint_start/status/result` | `validate_spec` 8-signal brownfield gate |
| OAuth 2.1 + Entra + Solution Architect group gating + owner_id isolation | Two-stage `/speckit.plan.draft` + `.review` |
| Blueprint artifact store (GCS + AlloyDB pointer) | `map_current_to_target` rules engine + substitution-row schema |
| Findings store + `verify_generation_gate` (Critical/High block, tech-debt JSON) | ADR predicate DSL interpreter + adr-rule schema |
| Eraser MCP synchronous render | brownfield `recommend_architecture` (per-integration retrieval) |
| `refresh` bidirectional sync engine | design-contract v2.0 schema + four-diagram assembly |
| Pre-commit hook + inner-loop eval emission | brownfield skill + migration templates (proxy/bridge/dual-write/cutover/decommission) |
| Live-service seam pattern (Vertex/Gemini/GCS/AlloyDB/Eraser/API Hub) | reference case (vSphere MPA → AWS SPA) |
| PRS scanner (extend, don't rebuild) | brownfield PRS rules (rollback path, coexistence telemetry) |

---

## Sequencing & dependencies

```
Phase 0 (schemas/templates/CLAUDE.md/ref-case skeleton)
  └─> Phase 1 (spec + 8-signal gate)
        └─> Phase 2 (R-factor plan, Plan Gate)
              └─> Phase 3 (map_current_to_target)         [deterministic]
                    └─> Phase 4 (recommend_architecture)  [LLM] ──┐
                    └─> Phase 5 (adr_compliance_check)     [det.] ─┤
                          └─> Phase 6 (assemble_blueprint + contract v2.0 + 4 diagrams)
                                └─> Phase 7 (assess + generation gate)   [reuse]
                                      └─> Phase 8 (brownfield generation skill)
                                            └─> Phase 9 (contract lifecycle + refresh)
                                                  └─> Phase 10 (reference case e2e + docs)
```
Phases 4 and 5 can proceed in parallel after Phase 3 (both consume `tech_substitutions[]`); Phase 6
needs both.

## Risks & honest caveats

- **Decision-table + ADR-rule CONTENT is human-authored** (EA / platform eng). The plan builds the
  engines, schemas, and tests; the rows/predicates and the recommend prompt are not code I can invent.
  This is the brownfield analogue of the greenfield "RAG corpus not built" gap and gates end-to-end runs.
- **Live-service calls remain seams** (Vertex AI Search, Gemini, GCS, AlloyDB, Eraser MCP, API Hub) —
  brownfield reuses the same commented-out-live-call pattern; wiring is credential/SDK work, not design.
- **Binary diagrams** (PNG/SVG) need a headless-render machine to regenerate; inline mermaid + `.mmd`
  are the source of truth.
- **CSA Agent is an upstream external dependency** — we parse its diagram output; we do not build it.
