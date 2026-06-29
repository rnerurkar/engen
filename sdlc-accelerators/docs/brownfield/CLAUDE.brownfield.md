# CLAUDE.md — SDLC Accelerators · Brownfield (CSA→TSA) Archetype

> This file is the brownfield counterpart to the root `CLAUDE.md`. It establishes the conventions, constraints, and architecture every brownfield (Current-State → Target-State Architecture migration) generation must respect. Where this file and the root `CLAUDE.md` agree (tech stack, NEVER-SWAPPABLE components, two-gates-only, IP boundary), the root governs; where brownfield differs (the four migration tools, the design contract v2.0, R-factor decisions, safe-migration validation), this file governs. Read `docs/csa-tsa-architecture.md` for the "why"; this file is the "how" for brownfield generation.

## Model & working mode

Use **Claude Opus 4.8** for this repo. Default to **plan mode** for any multi-file module: present the approach, get approval, then generate. Generate code and tests together, run the tests, self-correct.

Brownfield-specific working rule: **safety before completeness.** A brownfield migration touches a RUNNING production system with real users and real data. When a decision trades migration safety (rollback, coexistence, data integrity) against speed or elegance, choose safety and flag the tradeoff. A wrong brownfield call loses data; a wrong greenfield call is redesignable.

## What the brownfield archetype is

The brownfield archetype converts a **Current-State Architecture (CSA)** into a **Target-State Architecture (TSA)** — wholly or selectively. The developer supplies:
- a **CSA diagram** (produced upstream by the CSA Agent — an external dependency, NOT part of this platform),
- a **`spec.md`** (which integrations exist, their tech+version, type, data-flow direction, criticality, coexistence constraints, API contracts, state, volume/SLA) generated from `spec-template.md`, and
- a **`plan.md`** (the **R-factor** per integration — rehost / replatform / refactor / rearchitect / retire — plus cutover strategy and sequencing) generated from `plan-template.md`.

The **Solution Accelerator** turns spec+plan into a TSA `app-blueprint` (markdown + JSON design contract + four diagrams) via four deterministic-and-one-LLM tools; the **Governance Guardian** assesses it; skill-guided, brownfield-aware generation produces migration code (Strangler-Fig proxies, message bridges, dual-write windows, cutover gates).

**Selective vs. whole conversion:** the spec names which portion of the CSA to convert (per-integration scope), and the plan names the R-factor for each. Integrations not in scope stay as-is and are represented in the transition diagrams as coexistence boundaries.

## Tech stack (pinned)

Inherits the root `CLAUDE.md` tech stack verbatim (Python 3.12, ADK 2.0, MCP 2025-03-26, Cloud Run, AlloyDB, Vertex AI Search, Apigee API Hub, Eraser MCP server, Terraform, cosign + Binary Authorization, Model Armor). Brownfield adds no new pinned technologies — it adds tools, schema, and skills on the same stack.

## NEVER-SWAPPABLE components

Same as root, with one brownfield addition:
- **cosign**, **Binary Authorization**, **Vertex AI Search**, **Model Armor**, and **the design-contract schema** — fixed.
- Brownfield addition: **the Tech Substitution Decision Table is a deterministic rules engine — NEVER an LLM.** A missing `(source_tech, r_factor, context)` row goes to `unresolved[]` and errors out to the platform-engineering review queue. No LLM fallback for substitutions, ever. (The ONE LLM stage is `recommend_architecture` pattern selection.)

## Architecture: two governance gates only

Same as root — **Design Gate** and **Plan Gate** only. Eval and promote are downstream CI/CD. Brownfield's Plan Gate is heavier (the two-stage `/speckit.plan.draft` + `/speckit.plan.review` R-factor process), but it is still the Plan Gate — do not invent new gates.

## The four brownfield tools (the heart of this archetype)

The Solution Accelerator exposes the SAME async front door (`blueprint_start/status/result`) but runs a brownfield 4-tool pipeline internally. Generate these as deterministic-first, LLM-only-where-stated:

| Tool | Determinism | Role |
|---|---|---|
| `map_current_to_target` | **DETERMINISTIC** (rules engine) | Context-filtered decision table: `lookup(source_tech, r_factor, {criticality, data_size_class, compliance_regime, messaging_pattern, region_constraints, partner_constraints, ...})` (≤12 context dimensions, CI-enforced). Most-specific matching row wins; ties → `requires_review`. Output: `tech_substitutions[]` + `unresolved[]`. No match → error to review queue. |
| `recommend_architecture` | **LLM (the only one)** | Per integration: build query vector from intent + `functional_category[]` + `target_tech`; hybrid-search Pattern Catalog (Vertex AI Search); filter by `r_factor_supports[]`; LlmAgent picks from top-K; confidence = score gap. Then deterministic `validate_composition(pattern_tree)`. Confidence < 0.65 → `requires_review: true`. |
| `adr_compliance_check` | **DETERMINISTIC** (predicate DSL interpreter) | Per (integration, target_tech, pattern): query ADR Constraint Store by `(source_tech, target_tech, functional_category, r_factor)`; evaluate predicates in a constrained DSL (≤25 identifiers, parser-combinator, **no `eval()`**, ≥3 positive + ≥3 negative tests per rule). Output: `pass` (+`attested_adrs[]`) / `flag` / `reject`. |
| `assemble_blueprint` | **DETERMINISTIC** | Build `app-blueprint.md` (one block per integration: pattern + substitution + IaC modules + attested ADRs) + four diagrams (Component end-state, Sequence end-state, Sequence transition, Infrastructure). Inject Phase-0 cross-cloud coordination entry when topology requires it. Emit design contract `lifecycle: LIVE` with `staleness_triggers`. |

## validate_spec — the 8-signal brownfield migration-readiness gate

Before the pipeline runs, `validate_spec` runs at **two layers** (local SpecKit preset during `/speckit.specify`, and server-side as Step 0 of `blueprint_start`). It produces a `migration_readiness_score` (0–100) and a `phase_assignment_preview` (Phase 1 read-path / Phase 2 write-path / Phase 3 decommission). The eight signals, each PASS/WARN/BLOCK: **CSA Completeness, Integration Type, Data Flow Direction, Criticality Rating, Coexistence Constraints, API Surface, State Management, Data Volume + SLA.** Any BLOCK → `blueprint_start` returns immediately with specific guidance. This gate prevents data loss, not just bad architecture.

## Protected identifiers — do NOT rename

- Async tool names: `blueprint_start`, `blueprint_status`, `blueprint_result` (shared with greenfield).
- Brownfield tool names: `map_current_to_target`, `recommend_architecture`, `adr_compliance_check`, `assemble_blueprint`, `validate_composition`.
- Artifact names: `app-blueprint.md`, `app-blueprint.json`, **`design_contract.json`** (brownfield's contract artifact; schema_version 2.0).
- Commands: `/speckit.specify`, `/speckit.plan.draft`, `/speckit.plan.review`, `/accelerator.{blueprint,assess,generate,refresh}`.
- Component names: `Governance Guardian`, `CSA Agent` (upstream), `ADR Constraint Store`, `Tech Substitution Decision Table`.

## R-factor vocabulary (fixed)

The R-factor per integration in `plan.md` is one of: **rehost** (lift-and-shift), **replatform** (lift-tinker-shift), **refactor** (restructure for the target), **rearchitect** (redesign the integration), **retire** (decommission). The decision table and pattern catalog are keyed on these. Do not invent additional R-factors or synonyms.

## Directory conventions (brownfield additions)

```
skills/domain-skills/brownfield-migration.SKILL.md   — the brownfield generation skill (to author)
templates/code/brownfield-migration/                 — Jinja2 templates: strangler proxy, message bridge,
                                                        dual-write window, cutover gate, decommission job
templates/spec/spec-template.brownfield.md           — integration-block spec (8-signal fields)
templates/plan/plan-template.brownfield.md           — R-factor + cutover + sequencing per integration
schemas/design-contract.schema.json                  — design contract v2.0 (brownfield)
schemas/tech-substitution-row.schema.json            — one decision-table row
schemas/adr-rule.schema.json                          — one ADR predicate rule
services/solution-accelerator/src/brownfield/         — map_current_to_target, adr predicate interpreter,
                                                        brownfield pipeline orchestration
examples/vsphere-mpa-aws-spa/                         — the brownfield golden reference (the reference case)
```

## Coding standards (brownfield specifics on top of root)

- The decision table and ADR predicate interpreter are **deterministic, no `eval()`, parser-combinator style**. Identifier ceilings (12 context dims; 25 ADR identifiers) are **CI-enforced** — generate the CI check too.
- Every decision-table row and every ADR rule ships with **≥3 positive + ≥3 negative unit tests**. No rule merges without them.
- `tech_substitutions` with no matching row must **error**, not guess. Surface `unresolved[]`.
- Every migration code artifact (proxy, bridge, dual-write, cutover gate) must have a **rollback path** and emit the coexistence/cutover telemetry the transition diagram references.

## The vSphere MPA → AWS SPA reference case is the golden reference

`examples/vsphere-mpa-aws-spa/` is the brownfield analogue of FNOL. It contains the CSA diagram, `spec.md` (integrations with 8-signal fields), `plan.md` (R-factor per integration), and the expected `app-blueprint.md` + `design_contract.json` + four diagrams. Rules:
- Generating the **brownfield pipeline** → this spec/plan are the test input; the blueprint + contract are the expected output.
- Generating **`map_current_to_target`** → the reference case's `tech_substitutions[]` (e.g. IBM MQ → AWS SQS, refactor) is the golden output for those rows.
- Generating **`adr_compliance_check`** → the reference case's `attested_adrs[]` is the golden audit trail.
- If a module can't process the reference case end-to-end, it isn't done.

## How to work in this repo (brownfield)

1. Read this file, the root `CLAUDE.md`, and the nearest per-service `CLAUDE.md`.
2. For any module, read the relevant schema in `schemas/` FIRST (design-contract v2.0, substitution-row, adr-rule).
3. Read `docs/csa-tsa-architecture.md` for the stage, and the reference case for the fixture.
4. Plan mode before multi-file changes; get approval.
5. Generate code + tests together (incl. the ≥3/≥3 rule tests and the CI identifier-ceiling check); use the reference case as the fixture; run the tests.
6. When a task touches a NEVER-SWAPPABLE component, the design-contract schema, or would put an LLM in the substitution path, STOP and flag it.

## What NOT to generate (brownfield)

- **No LLM in the substitution path.** `map_current_to_target` and `adr_compliance_check` are deterministic. Only `recommend_architecture` pattern selection is LLM.
- No eval-gate or promote-gate logic (downstream CI/CD owns it).
- No substitutes for NEVER-SWAPPABLE components; no renaming of protected identifiers.
- No migration code without a rollback path and coexistence telemetry.
- The **decision-table rows, ADR rule predicates, and the recommend_architecture curated prompt are human-authored** (EA office / platform engineering) — scaffold the engine, the schema, and the tests, but do not invent the migration judgment or the rule content.
- **IP boundary:** never introduce meta-skills, STL, or the external platform-style signed Design Contracts. SDLC Accelerators brownfield = deterministic rules engine + RAG pattern selection + skill-constrained generation. The `design_contract.json` here is a brownfield governance artifact (schema 2.0), NOT an the external platform signed Design Contract — zero overlap.
