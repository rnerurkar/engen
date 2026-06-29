# ARB Review — SDLC Accelerators (Greenfield + Brownfield)
### Epic → Spec → Design Blueprint via the Solution Accelerator Agent

**Reviewer:** Chief Architect / Engineer (ARB)
**Scope:** All design + code artifacts in the SDLC Accelerators package — both archetypes. Focus axes: **accuracy**, **completeness**, **adherence to the Epic→spec→blueprint design approach**, plus two directed checks: (a) zero use of any foreign product term, and (b) the no-match → create-new behavior for skills and tools.
**Verdict:** **Pass (all findings resolved).** Originally Conditional Pass; One Critical and one High finding were material; both were **remediated in this review pass** and re-verified. Remaining findings are Medium/Low and do not block, but should be scheduled.

---

## Findings summary

| ID | Sev | Area | Finding | Status |
|----|-----|------|---------|--------|
| C-1 | **Critical** | Term hygiene / IP | Foreign product term used pervasively in employer artifacts (119 occurrences / 24 files, incl. 2 diagrams + 2 dedicated comparison docs) | ✅ Resolved this pass |
| H-1 | **High** | Completeness / design adherence | No-match → create-new not implemented: no new `SKILL.md` on Skill-Catalog miss; no new function-tool definition on A2A/MCP miss; model could not even represent a "to-create" skill | ✅ Resolved this pass |
| M-1 | Medium | Accuracy / consistency | Brownfield **ingest** spec shape (8-field template) ≠ brownfield **sample/CSA-extractor** spec shape (richer "Current State" blocks) | ✅ Resolved |
| M-2 | Medium | API consistency | `blueprint_gate` key differs across archetypes (`quality_score` vs `migration_readiness_score`); one IDE consumer must branch | ✅ Resolved |
| M-3 | Medium | Scope / design intent | No-match → create-new for skills/tools is **greenfield-only by design** — brownfield modernizes an existing app via transition patterns and does not compose an agentic app, so it synthesizes no new skills/tools | ✅ Resolved (by design) |
| M-4 | Medium | Discoverability | Brownfield Epic front-door command lives outside the shared `.specify/commands/` registry the greenfield command uses | ✅ Resolved |
| L-1 | Low | Clarity | Greenfield ingest samples are partial drafts (gate 35–50, many `[NEEDS CLARIFICATION]`) but the relationship to each sample's completed `spec.md` is only lightly documented | ✅ Resolved |
| L-2 | Low | Robustness | Brownfield staleness header regex matches the literal word "Epic"; a body mention could mis-parse (durable ledger sidecar mitigates) | ✅ Resolved |
| L-3 | Low | Hygiene | Divergent payload shapes for the two same-named `recommend_architecture` FunctionTools (`{spec,plan}` vs `{substitution,candidates}`) are undocumented | ✅ Resolved |

Positive notes (design adherence is strong): the **extractive + span-grounded** guarantee is enforced identically in both archetypes (verbatim `epic_span` **and** value-grounding — no fabricated/altered quantities); the **agent genuinely executes** via direct capability dispatch (no LLM tool-router); confidence is a **deterministic fill ratio**, not agent-reported; staleness uses the **Rally ObjectVersion** token from a durable sidecar; and the blueprint **gate is reconciled** against the produced spec (H-3 from the prior greenfield ARB, now mirrored in brownfield).

---

## Critical

### C-1 — Foreign product term in employer artifacts *(Resolved this pass)*
**Finding.** The term naming the founder's separate commercial platform appeared **119 times across 24 files**, including two rendered diagrams (`*-steps-4-7-internals.svg/png`), code comments in both `solution_accelerator_agent.py` modules and the greenfield pipeline/orchestrator, the ingest models, two schemas, two system prompts, several build-report/README docs, and **two dedicated comparison documents** (`…-IP-Analysis.md`, `…-IP-Separation.md`). Naming an external personal-venture product inside the employer's product artifacts is an IP-hygiene and provenance problem regardless of intent.

**Resolution.** Scrubbed every occurrence to neutral, self-contained phrasing (e.g. IP-boundary panels now read *"claimed novelty vs shared ADK patterns"*; *"a shared ADK design-agent-with-tools pattern, not a distinguishing claim"*; *"out-of-scope external IP"*). The two comparison documents — whose entire subject and filenames were the foreign term — were **removed from the deliverable** (retained outside the package as private analysis). Both diagrams were re-rendered. **Verification:** 0 occurrences remain in content or filenames (case-insensitive). The substantive IP boundary (what *is* claimed vs. what is a shared pattern) is preserved without naming the external product.

---

## High

### H-1 — No-match → create-new for skills and tools was not implemented *(Resolved this pass)*
**Finding (validation result).** The directed check failed as written. The pipeline **matched** skills/tools via RAG but had **no path to synthesize a definition when nothing matched**:
- **Skills.** `SkillSelection` *required* `sha` + `version` (existing-catalog provenance) — it was structurally **incapable of representing an unmatched skill to be created**. There was no SKILL.md generation, and `app-blueprint.json` carried no instruction to create one. The blueprint **schema modeled no `skills` at all**.
- **Tools.** The A2A > MCP > Build priority existed **only as prose in the system prompt**. `ToolSelection` had no matched-vs-create `status` and no definition payload, so the coding agent could not distinguish "bind this existing tool" from "build this new one," and received no I/O contract for the new tool.

**Resolution (implemented + tested).**
- `ToolSelection` / `SkillSelection` gained `status: matched | to_create` and a `definition`. `sha`/`version` are now optional (empty for to-create).
- `recommend_architecture`'s system prompt now instructs: resolve each capability **A2A > MCP > Build**; on a total miss emit a `function_tool` with `status:"to_create"` + `definition {description, input_schema, output_schema, rationale}`; on a Skill-Catalog miss emit a skill with `status:"to_create"` + `definition {description, skill_md}` where `skill_md` is a full **SKILL.md** (frontmatter + body); never fabricate a `sha`/`version` for an unmatched skill.
- The deterministic assembly surfaces both in `app-blueprint.json → to_create.{skills, function_tools}` (and stamps `status`/`definition` on each binding), and `app-blueprint.md` renders a **"New skills & tools to create — YOUR CODE HERE"** callout. The coding agent (`/accelerator.generate`) writes `skills/<name>/SKILL.md` and implements the new FunctionTool from these.
- Schema updated (`skills[]`, `to_create`, tool `status`/`definition`). New test `test_skill_tool_creation.py` proves an unmatched skill → `to_create.skills` with SKILL.md and an unmatched tool → `to_create.function_tools` with I/O schema, while matched items keep provenance/binding. Existing suites still pass.

**Scope (see M-3).** This is, and stays, **greenfield-only** — greenfield composes a new agentic app, so it must define new skills/tools when the catalog/API-Hub misses. Brownfield modernizes an existing application via deterministic transition patterns and does **not** create an agentic app, so it intentionally synthesizes no new skills or tools.

---

## Medium

### M-1 — Brownfield ingest spec shape diverges from the sample/CSA-extractor shape
The brownfield **ingest** (`mapping.py`) renders the flat 8-field template (`- **Technology + version:**`, `- **Integration type:**`, …) that `spec_parser` + `validate_spec` consume. The brownfield **samples** (and the `/speckit.specify` `csa-extractor` output) use a **richer** block (`**Current State**` → Protocol / Transport / Auth / Stack, `**Functional category:**`, etc.). So `spec.ingested.md` and a sample's own `spec.md` are **not the same shape**, and the front-door draft will not round-trip through the sample/CSA-extractor format without transformation.
*Recommendation:* either (a) render the ingest output in the richer Current-State format the csa-extractor reconciles, or (b) document explicitly that ingestion emits the **canonical readiness template** and `/speckit.specify` up-converts it. Pick one and make the two parsers agree.

### M-2 — `blueprint_gate` key naming differs across archetypes
Greenfield returns `quality_score`; brownfield returns `migration_readiness_score`. Both also return `blocked`, `findings`, `high_confidence_but_gated`. A single IDE consumer must branch on archetype.
*Recommendation:* add a common `score` alias (keep the specific key too) so the front door has one stable contract.

### M-3 — No-match → create-new is greenfield-only (by design)
**Resolution: by design, not a gap.** Skill/tool synthesis exists only in **greenfield**, which composes a *new agentic application* and therefore must emit new SKILL.md / FunctionTool definitions (associated with their agents via `assigned_to`) when semantic search misses. **Brownfield is modernization, not agentic-app creation**: it maps each existing integration to a target via deterministic CSA→TSA transition patterns and substitutions; it does not build an agent topology and so has no skills/tools to synthesize. Accordingly the brownfield design contract carries **no** `to_create`/`tool_bindings` block. This is now stated explicitly in `csa-tsa-architecture.md`.

### M-4 — Brownfield Epic command outside the shared command registry
The greenfield front door is `.specify/commands/accelerator.ingest-epic.md`; the brownfield one was added at `brownfield/commands/accelerator.ingest-epic.brownfield.md`. Discovery is inconsistent across archetypes.
*Recommendation:* register the brownfield front door in the same command surface (or document the split clearly in both developer guides).

---

## Low

- **L-1 — Partial-draft framing.** Greenfield ingest samples score 35–50 with several `[NEEDS CLARIFICATION]` (by design — only Epic-derivable sections are filled). The link between the sparse `spec.ingested.md` and the completed `spec.md` is only in the README lineage line. *Recommendation:* one sentence per sample stating the ingest draft is intentionally partial and completed during `/specify`.
- **L-2 — Staleness header regex.** Brownfield `read_provenance_from_spec` keys off the literal word "Epic"; a body occurrence could mis-parse. The durable ledger sidecar is preferred, so impact is low. *Recommendation:* anchor the regex to the provenance-comment lines.
- **L-3 — Divergent FunctionTool payloads.** The two same-named `recommend_architecture` tools take different payloads (`{spec,plan}` vs `{substitution,candidates}`). Acceptable (separate services) but undocumented. *Recommendation:* note it in both architecture docs.

---

## Resolution log (this pass)
1. **C-1** — scrubbed the foreign term everywhere (0 remaining; 2 comparison docs removed; 2 diagrams re-rendered).
2. **H-1** — implemented no-match → create-new for skills (SKILL.md) and tools (function_tool definition, A2A>MCP>Build), across model + harness + assembly + schema + system prompt + test; verified.

Re-verification after this pass: greenfield suite green (incl. the new test) + greenfield ingest smoke; brownfield 47 passed (the 7 failures are the pre-existing `google.adk`-not-installed orchestrator tests — environmental, not regressions); all 12 sample ledgers schema-valid; both archetypes' Epic→spec extractive guarantee intact.

*Not legal advice — patent-claim language and IP-boundary wording should still be confirmed with a practitioner.*


---

## Closure log — second pass (M-1 … L-3 resolved)
- **M-1** — documented the format contract: ingestion emits the canonical 8-signal readiness template (`spec_parser`/`validate_spec` shape); `/speckit.specify`'s csa-extractor up-converts it to the Current-State inventory and reconciles against the CSA diagram. Noted in the mapping provenance header, `csa-tsa-architecture.md`, and both copies of the brownfield ingest command.
- **M-2** — added an archetype-agnostic `score` alias to both `blueprint_gate` verdicts (the specific `quality_score` / `migration_readiness_score` keys are retained for back-compat).
- **M-3** — resolved **by design**: no-match → create-new is greenfield-only. Greenfield composes a new agentic app and emits new skill/tool definitions on a miss; brownfield modernizes an existing app via transition patterns and creates no agent skills/tools. The brownfield design contract carries no `to_create` block, and `csa-tsa-architecture.md` now states this explicitly. (An earlier draft added a brownfield `to_create`; it was removed as architecturally incorrect.)
- **M-4** — registered the brownfield Epic front door in the shared `.specify/commands/` registry alongside the greenfield command (brownfield-local copy points to it).
- **L-1** — prepended a partial-draft framing note to every sample `spec.ingested.md` (11 samples).
- **L-2** — anchored the brownfield staleness regex to the `Rally Epic` provenance phrasing so a bare body mention of 'Epic' is no longer mis-parsed (verified).
- **L-3** — documented the divergent `recommend_architecture` payloads (`{spec,plan}` vs `{substitution,candidates}`) in `csa-tsa-architecture.md`.

Re-validation: greenfield **17 passed**, brownfield **59 passed** (ADK SDK now declared so the orchestrator integration tests run), 0 cross-product IP leaks (C-1 re-verified), all 9 findings verified closed; skill/tool creation confirmed greenfield-only.