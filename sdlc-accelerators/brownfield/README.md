# SDLC Accelerators — Brownfield (CSA → TSA) Archetype

The brownfield archetype converts a **Current-State Architecture (CSA)** into a **Target-State
Architecture (TSA)** — wholly or selectively. A developer supplies a CSA diagram (from the upstream
CSA Agent), a `spec.md` (which integrations exist + the 8 migration-readiness signals), and a
`plan.md` (the **R-factor** per integration + cutover strategy). The **Solution Accelerator** turns
spec+plan into a TSA `app-blueprint` (markdown + `design_contract.json` v2.0 + four diagrams) via
four migration tools; the **Governance Guardian** assesses it; brownfield-aware generation produces
migration code (Strangler-Fig proxies, dual-write windows, cutover gates) — each with a rollback path.

This folder is self-contained. It reuses the platform spine (async MCP front door, OAuth + group
gating, GCS + AlloyDB stores, generation gate, refresh) and adds the brownfield-specific pieces.

> Generation context lives in `../docs/brownfield/CLAUDE.brownfield.md`; the phased build plan in
> `../docs/brownfield/BROWNFIELD-IMPLEMENTATION-PLAN.md`; the architecture/dev-guide/playbook in
> `../docs/csa-tsa-*.md`.

## Repo map

```
brownfield/
  README.md                         — this file
  src/brownfield/                   — the engine
    spec_parser.py                  — parse the 8-signal integration blocks
    validate_spec.py                — 8-signal migration-readiness gate (PASS/WARN/BLOCK)
    plan_parser.py                  — R-factor + cutover + context per integration
    map_current_to_target.py        — Tool 1: deterministic context-filtered decision table
    adr_predicate.py                — no-eval() predicate DSL interpreter
    adr_compliance_check.py         — Tool 3: deterministic ADR policy (pass/flag/reject)
    assemble_blueprint.py           — Tool 4: blueprint + design contract v2.0 + four diagram DSLs
    pipeline.py                     — chains the four tools (Tool 2 is the LLM seam)
    generator.py                    — migration code generator + rollback-path PRS rule
  schemas/                          — design-contract v2.0, tech-substitution-row, adr-rule
  templates/
    spec/spec-template.brownfield.md
    plan/plan-template.brownfield.md
    code/brownfield-migration/      — strangler_proxy, dual_write, cutover_gate (.j2)
  skills/domain-skills/brownfield-migration.SKILL.md
  examples/vsphere-mpa-aws-spa/     — the reference case (brownfield's FNOL)
    inputs/   — csa diagram, spec.md, plan.md, substitution-table.json
    outputs/  — app-blueprint.md, design_contract.json, diagrams-dsl.md
  tests/                            — pytest (run from repo root: pytest brownfield/tests/)
```

## Getting started

```bash
# from the repo root
python -m pytest brownfield/tests/ -q        # 26 brownfield tests
ruff check brownfield/

# run the reference case end-to-end
python - <<'PY'
import sys, json; sys.path.insert(0, 'brownfield/src')
from brownfield.map_current_to_target import SubstitutionRow
from brownfield.pipeline import run_brownfield_pipeline
ref = 'brownfield/examples/vsphere-mpa-aws-spa'
rows = [SubstitutionRow(**r) for r in json.load(open(f'{ref}/inputs/substitution-table.json'))['rows']]
r = run_brownfield_pipeline(open(f'{ref}/inputs/spec.md').read(), open(f'{ref}/inputs/plan.md').read(),
                            rows, adr_rules=[],
                            recommend_fn=lambda s: {"pattern_ref": s["transition_pattern_ref"], "confidence": 0.9, "requires_review": False})
print(r["readiness"], r["design_contract"]["lifecycle"], r["design_contract"]["schema_version"])
PY
```

## The flow (10 stages → four tools)

1. **CSA Agent (upstream)** produces a validated CSA diagram — external dependency, not built here.
2. **`/speckit.specify`** — the csa-extractor parses the diagram, pre-fills integration blocks; you
   add the 8-signal fields. → `spec.md`.
3. **`/speckit.plan.draft` + `/speckit.plan.review`** — two-stage R-factor decisions (Plan Gate). → `plan.md`.
4. **`/accelerator.blueprint`** — async `blueprint_start/status/result`. Step 0 is **`validate_spec`**.
5. **Tool 1 `map_current_to_target`** — deterministic CSA→TSA substitution (no LLM fallback).
6. **Tool 2 `recommend_architecture`** — the one LLM stage (RAG pattern selection) + `validate_composition`.
7. **Tool 3 `adr_compliance_check`** — deterministic predicate DSL → pass/flag/reject + attested ADRs.
8. **Tool 4 `assemble_blueprint`** — blueprint + `design_contract.json` v2.0 + four diagrams.
9. **`/accelerator.assess`** + **`verify_generation_gate`** (reused from the platform spine).
10. **`/accelerator.generate`** — brownfield-aware migration code, each artifact with a rollback path.

## Reference case — vSphere MPA → AWS SPA

`examples/vsphere-mpa-aws-spa/` is the brownfield analogue of FNOL. Four integrations:
INT-001 (JSP→CloudFront/S3, refactor), INT-002 (Tomcat→Spring Boot/Fargate, refactor),
INT-003 (APIC→Apigee, replatform, **cross-cloud**), INT-004 (IBM MQ→SQS, refactor, 48h dual-publish).
If a module can't process this case end-to-end, it isn't done.

## Implementation status

**26 brownfield tests passing (118 platform-wide), clean lint.** The reference case runs end-to-end.

### ✅ Fully implemented and tested
| Component | Where |
|---|---|
| Spec parser + 8-signal `validate_spec` gate (readiness score, phase preview) | `spec_parser.py`, `validate_spec.py` |
| Plan parser (fixed R-factor vocabulary; rejects synonyms) | `plan_parser.py` |
| Tool 1 `map_current_to_target` (most-specific-wins, priority tie-break, ties→review, unresolved→error, 12-dim ceiling, token normalization) | `map_current_to_target.py` |
| Tool 3 `adr_compliance_check` + no-`eval()` predicate DSL (25-id ceiling, ≥3/≥3 rule-test guard) | `adr_compliance_check.py`, `adr_predicate.py` |
| Tool 4 `assemble_blueprint` (one block/integration, four diagram DSLs, cross-cloud Phase-0, contract v2.0) | `assemble_blueprint.py` |
| Brownfield pipeline (chains the four tools) | `pipeline.py` |
| Migration generator + rollback-path PRS rule | `generator.py` |
| Skill + migration templates (strangler/dual-write/cutover) | `skills/`, `templates/code/brownfield-migration/` |
| Schemas (design-contract v2.0, substitution-row, adr-rule) | `schemas/` |
| Reference case (inputs + generated outputs) | `examples/vsphere-mpa-aws-spa/` |

### ⚙️ Logic built — live call / injection is a marked seam
| Seam | Note |
|---|---|
| **Tool 2 `recommend_architecture`** | **WIRED** — `recommend_architecture.py` reuses the platform's live Gemini provider; binds the authored brownfield prompt verbatim, applies the <0.65 confidence→review threshold. Pipeline routes through it by default; tests inject `recommend_fn`. Degrades to `requires_review` when unconfigured. Pattern candidate retrieval (Vertex AI Search) remains a RAG seam. |
| **CSA-diagram extractor** | Parses the upstream CSA diagram; reuses the platform's diagram-parsing seam. |
| **Eraser MCP render** of the four diagram DSLs | Reuses the platform's synchronous render seam. |
| **GCS + AlloyDB persistence** of the blueprint + contract | Reuses the platform artifact/findings stores (GCS + AlloyDB pointer). |

### 🔴 Human-authored content (not code)
| Item | Note |
|---|---|
| **Decision-table rows** | Authored by platform engineering (Operating Playbook §5). The engine + schema + ceiling check are built; the rows are content. |
| **ADR rule predicates** | Authored by the EA office (Operating Playbook §4). The interpreter + ≥3/≥3 test guard are built; the predicates are content. |
| **Pattern Catalog corpus** | The transition patterns retrieved by Tool 2 must be ingested (shared with greenfield's RAG corpus gap). |

### What "done" looks like
The deterministic spine (gate + three deterministic tools + assembly + generation) is built and
tested. To reach a live brownfield platform: (1) author the decision-table rows, ADR predicates, and
transition-pattern corpus; (2) wire Tool 2's LLM + the shared live-service seams; (3) run the
reference case on live infra. None of the ⚙️ seams require new design.
