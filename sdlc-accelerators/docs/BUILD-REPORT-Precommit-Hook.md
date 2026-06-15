# Build Report — Pre-commit Hook (lint + inner-loop eval on commit)

Closes the gap where `.pre-commit-config.yaml` was documented as "always generated" but the
generator didn't emit it. **77 tests passing, clean lint.**

## What's built
- `templates/code/agentic-ai-adk/.pre-commit-config.yaml.j2` — wires two hooks:
  - **ruff** (lint --fix + format)
  - **inner-loop-eval** (`python tests/eval_inner_loop.py`) on `stages: [commit]`
  Header documents the one-time `pip install pre-commit && pre-commit install`.
- `templates/code/agentic-ai-adk/eval_inner_loop.py.j2` — the inner-loop eval script:
  golden-dataset quality gate (≥10/agent, ≥3 edge cases, ≥1 negative — deterministic) +
  >10% regression gate (deterministic); the Vertex AI Evaluation SDK scoring call is the seam.
- `generator/adk_renderer.py` — now emits both files (constitution Rules 11/13). Generated
  `.py` count went 14 → 15 (the eval harness); tests updated accordingly.

## Validations (tested)
- ✅ Generator emits `.pre-commit-config.yaml` + `tests/eval_inner_loop.py`
- ✅ Config contains the ruff hook, the inner-loop hook, and the install instruction
- ✅ PRS scanner no longer flags `.pre-commit-config.yaml` as a missing required artifact
- ✅ The hyphen-subtraction AST guard scoped to name-interpolated files (agents/tools/main),
  so the eval harness's legitimate arithmetic doesn't false-positive

## README
Added a **"Commit-time checks (linting + inner-loop eval in VS Code)"** section: the one-time
`pre-commit install`, what runs on each commit, the blocking conditions, and the honest note that
the eval SDK call is a live seam while lint + the dataset gate run today.

## Seam
The Vertex AI Evaluation SDK scoring call inside `eval_inner_loop.py` (gate logic is real).
