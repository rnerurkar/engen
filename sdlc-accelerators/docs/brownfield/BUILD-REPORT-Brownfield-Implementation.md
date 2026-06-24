# Build Report — Brownfield (CSA→TSA) Implementation

Implemented the brownfield archetype following `CLAUDE.brownfield.md` and the implementation plan,
organized under a self-contained `brownfield/` folder, fully branded SDLC Accelerators / Solution
Accelerator / `/accelerator.*`. **118 tests passing (26 brownfield + 92 greenfield), clean lint.**

## What was built (Phases 0–8 of the plan)
- **Phase 0 — foundations:** `brownfield/` folder; schemas (design-contract v2.0, tech-substitution-row,
  adr-rule); brownfield spec/plan templates; reference-case skeleton.
- **Phase 1 — spec + gate:** `spec_parser.py`; `validate_spec.py` (8-signal migration-readiness gate,
  PASS/WARN/BLOCK, readiness score, phase-assignment preview).
- **Phase 2 — R-factor plan:** `plan_parser.py` (fixed R-factor vocabulary, rejects synonyms, context dims).
- **Phase 3 — Tool 1:** `map_current_to_target.py` — deterministic context-filtered decision table;
  most-specific-wins; priority tie-break; ties → review; unresolved → error (NO LLM fallback);
  12-dimension ceiling; hyphen/space token normalization.
- **Phase 5 — Tool 3:** `adr_predicate.py` (no-`eval()` recursive-descent interpreter, 25-identifier
  ceiling) + `adr_compliance_check.py` (pass/flag/reject, attested_adrs audit trail, ≥3/≥3 rule-test guard).
- **Phase 6 — Tool 4:** `assemble_blueprint.py` — one block per integration; four diagram DSLs;
  cross-cloud Phase-0 injection; design contract v2.0 LIVE (validates against schema).
- **Pipeline:** `pipeline.py` chains all four tools; readiness BLOCK raises; Tool 2 is the injected
  recommend seam (degrades to requires_review).
- **Phase 8 — generation:** `brownfield-migration.SKILL.md` + templates (strangler proxy, dual-write,
  cutover gate); `generator.py` picks template per cutover strategy; every artifact has a rollback path
  and coexistence telemetry; `check_rollback_paths` is the brownfield PRS rule.

## Reference case (vSphere MPA → AWS SPA)
Runs end-to-end: 4 integrations (INT-001…004), readiness 100/PASS, IBM MQ→SQS / APIC→Apigee /
JSP→CloudFront+S3 / Tomcat→Spring Boot+Fargate substitutions, cross-cloud Phase-0 auto-injected for
INT-003, design contract v2.0, four diagram DSLs, and per-strategy migration code. Outputs saved under
`brownfield/examples/vsphere-mpa-aws-spa/outputs/`.

## Rebranding
All brownfield deliverables use SDLC Accelerators / Solution Accelerator / `/accelerator.*`. The
existing platform and the three brownfield docs were already clean; the only AgentCatalyst mentions in
the repo are intentional "formerly AgentCatalyst" historical notes.

## Docs updated
- `csa-tsa-architecture.md`: added an Implementation Status section (✅ built / ⚙️ seams / 🔴 authored content).
- `csa-tsa-developer-guide.md` + `csa-tsa-operating-playbook.md`: status pointers.
- Root `README.md`: a Brownfield archetype section.

## Seams & human-authored content (honest gaps)
- **Tool 2 `recommend_architecture`** (the one LLM stage) is a seam — injected `recommend_fn`; live RAG +
  LlmAgent wiring pending (same pattern as greenfield).
- **Decision-table rows** and **ADR rule predicates** are human-authored (platform eng / EA office). The
  engines, schemas, and ≥3/≥3 test guards are built; the content gates end-to-end runs — the brownfield
  analogue of the greenfield "RAG corpus not built" gap.
- **Binary diagrams** (PNG/SVG) need a headless-render machine to regenerate.
