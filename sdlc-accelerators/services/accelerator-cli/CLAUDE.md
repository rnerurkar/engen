# CLAUDE.md — accelerator-cli

> Service-specific context. Read the root `CLAUDE.md` first.

## Role

Python CLI tool. Deterministic scaffold + governance gate. Reads `app-blueprint.json` (the DERIVED, machine-readable artifact — NOT the .md) and generates the complete project using company Jinja2 templates. Same JSON in → byte-identical output every time.

## The `/accelerator.*` commands

| Command | Definition file | Purpose |
|---|---|---|
| `/accelerator.blueprint` | `commands/accelerator.blueprint.md` | Calls Solution Accelerator (async) |
| `/accelerator.assess` | `commands/accelerator.assess.md` | Calls Governance Guardian (iterative) |
| `/accelerator.generate` | `commands/accelerator.generate.md` | Governance gate → code generation |
| `/accelerator.refresh` | `commands/accelerator.refresh.md` | Bidirectional .md ↔ .drawio sync |

## Governance gate (in `/accelerator.generate`)

```
1. recordTechDebt check → showstoppers? STOP. else resume.
2. Verify .json not stale (hash check against .accelerator-hashes)
   — if stale, auto-refresh first
3. Read app-blueprint.json
4. Generate via company Jinja2 templates:
   - ADK agents, MCP + A2A wiring, FunctionTools
   - Terraform (from resolved module interfaces)
   - CI/CD configs
   - Model Armor callbacks, Agent Identity, observability
5. The coding agent NEVER deploys — it reads .json, writes code, opens a PR
```

## Determinism requirement

This is the deterministic half of the platform. Given the same `app-blueprint.json` + same template version, output must be byte-identical. No LLM calls in the generation path. No randomness, no timestamps in generated content, sorted iteration order everywhere.

## Reads .json, never .md

The CLI consumes `app-blueprint.json` (structured: adk_agent_tree, tool_bindings, data_flows, infra_modules, etc.). The `.md` is for humans and the Governance Guardian; the CLI never parses prose.

## Templates

Jinja2 templates live in `templates/`. Generation is template-driven, not freeform. Adding a capability means adding/editing a template, not changing generation logic.

## Tests

Golden-file tests: given the FNOL `app-blueprint.json` fixture, assert the generated project matches a committed golden tree byte-for-byte. This is the determinism guarantee.
