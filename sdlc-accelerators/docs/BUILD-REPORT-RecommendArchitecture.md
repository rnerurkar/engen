# Build Report — recommend_architecture (reasoning pipeline)

Implements the full reasoning-time pipeline EXCEPT the model's own reasoning, which runs
the authored 8-step system prompt on Gemini (the single live seam). Spec/plan stay as
markdown throughout — never converted to JSON (architecture-faithful). **42 tests passing, clean lint.**

## Pipeline (architecture lines 209-214)
```
validate_spec (deterministic signal extraction + quality gate)
  -> retrieve (search_patterns + search_skills + discover_integrations)
  -> invoke_llm_agent (authored system prompt on Gemini — the live seam)
  -> parse_selections -> ArchitectureSelections
  -> [assemble_blueprint] -> app-blueprint.md + .json + Eraser DSL
```

## Components (services/solution-accelerator/src/reasoning/)
- `validate_spec.py` — DETERMINISTIC signal extraction from spec.md markdown:
  §2 ordering words, §5 own-system flags, §10 measurable criteria. Produces a
  spec_quality_score (0-100) + PASS/WARN/BLOCK per section with the documented guidance.
  Architecture line 138: explicitly "a quality gate, NOT a reasoning step."
- `llm_harness.py` — the LlmAgent call harness:
  - loads the authored 8-step system prompt (prompts/greenfield-system-prompt.md)
  - assembles the user message (spec.md + plan.md AS MARKDOWN + signals + retrieved context)
  - invoke_llm_agent() — the single live seam (inject model_fn in tests; bind ADK LlmAgent live)
  - parse_selections() — model JSON -> validated ArchitectureSelections
- `recommend_architecture.py` — chains all of the above; raises SpecBlockedError on BLOCK,
  raises NotImplementedError only at the live model seam if no model_fn provided.

## The authored reasoning
The 8-step system prompt (compose patterns, discover tools/agents, match skills w/ provenance,
resolve infra, ADR compliance, business-logic stubs, derive identity, assemble) drives the model.
It is loaded and passed verbatim — the harness does not fabricate the reasoning; it invokes it.

## Validations (all tested)
- ✅ Signal extraction finds ordering words / own-system flags / measurable criteria in real FNOL spec.md
- ✅ validate_spec PASSES FNOL (score ≥70), BLOCKS a spec with no ordering words (returns guidance)
- ✅ Harness loads the authored prompt; spec/plan remain markdown in the user message
- ✅ FULL pipeline: spec.md -> selections -> assemble_blueprint -> 9-section .md + .json + 2 diagrams
- ✅ Live-model boundary: run() without model_fn raises NotImplementedError (does not fabricate)

## Scope honesty
- Everything around the model is implemented and tested: validation, signal extraction, retrieval
  orchestration, prompt loading, context assembly, output parsing, and the chain into assembly.
- The ONE live seam is the Gemini call inside invoke_llm_agent. Tests inject a model_fn that
  returns FNOL-shaped output; production binds the live ADK LlmAgent. This is the authored-prompt
  reasoning — invoked, not fabricated.
- retrieve() returns empty until the RAG corpus is populated (ingestion pipeline); orchestration is real.
