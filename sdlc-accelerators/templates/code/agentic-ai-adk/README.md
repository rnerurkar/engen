# Agentic-AI (ADK) Domain Skill — Templates + Renderer

The first authored domain skill for `/accelerator.generate`. Turns an
`app-blueprint.json` (agentic-AI archetype) into production-ready Google ADK code.

## Contents

| File | Role |
|---|---|
| `../../skills/domain-skills/agentic-ai-adk.SKILL.md` | The skill definition (rules, mappings, validation) |
| `agent_sequential.py.j2` | SequentialAgent template |
| `agent_parallel.py.j2` | ParallelAgent template |
| `agent_llm.py.j2` | LlmAgent (+ optional LoopAgent retry) template |
| `agent_hitl.py.j2` | HITL CustomAgent (BaseAgent) template |
| `function_tools.py.j2` | FunctionTools from business_rules[] |
| `model_armor.py.j2` | Model Armor input/output screening callbacks |
| `main.py.j2` | Runtime entrypoint |
| `render.py` | Reference renderer (this logic moves into accelerator-cli) |

## Validate against FNOL

```
pip install jinja2
python render.py ../../../examples/fnol/outputs/app-blueprint.json ./out
# then: python -m py_compile out/**/*.py
```

Expected: 8 agents + function_tools + model_armor + main, all valid Python,
6 agents input-screened, 3 output-screened, deterministic across runs.

A committed reference output is in `examples/fnol/generated-sample/`.

## How this becomes accelerator-cli

`render.py` is the reference implementation. In Phase 3, the accelerator-cli
absorbs this logic: same templates, same Jinja2 environment (custom tests/filters),
driven by `app-blueprint.json`. The golden-file test asserts the CLI output matches
`examples/fnol/generated-sample/` byte-for-byte (the determinism guarantee).

## Known scaffolding gaps (Phase 4 human authoring)

- `function_tools.py.j2` scaffolds rule branches as TODO comments — the actual
  predicate extraction from `business_rules[].rule` prose needs human verification.
- `mcp_clients.py` / `a2a_clients.py` wiring templates are not yet authored (next).
- Agent Identity application (`identity/agent_identity.py`) template is next.

## Generalization — validated on a second use case

The renderer is schema-driven, not FNOL-shaped. Validated against a deliberately
different agentic use case (`examples/contract-review/`): LoopAgent at root, two A2A
agents, function tools beside A2A in one tools[] list, strict screening.

Building that second case surfaced and fixed four bugs that FNOL alone had masked:
1. LoopAgent as a NODE collapsed to an empty LlmAgent (child dropped) — added agent_loop.py.j2
2. A2A tools rendered as bare hyphenated identifiers (`legal-review-a2a` → invalid) — now get_a2a_agent("...")
3. model=null rendered as the string "None" — now omitted when null
4. A latent version of bug 2 existed in FNOL's body-shop-a2a too — now fixed

Lesson: py_compile is insufficient — hyphenated names parse as subtraction. Tests
now AST-check for accidental subtraction. Any new archetype/use case should be added
as a fixture here the same way.
