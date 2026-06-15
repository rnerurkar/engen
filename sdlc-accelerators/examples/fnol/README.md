# FNOL Claims Agent — Reference Example

This is the canonical worked example for the SDLC Accelerators platform. Every generated module should be able to process this example end-to-end. Claude Code uses these artifacts as the pattern to match against — they are the "demonstrated" reference, not just the "described" one.

## The FNOL scenario

First Notice of Loss (FNOL) claims intake for auto insurance. Pattern: **Sequential → Parallel (3× Loop) → HITL**.

```
fnol_coordinator (SequentialAgent)
  ├── extract_details (LlmAgent)              — claims-db-mcp, coverage_calculator_fn
  ├── parallel_enrichment (ParallelAgent)
  │     ├── enrich_policy (LlmAgent + LoopAgent retry)    — policy-api-mcp
  │     ├── enrich_vehicle (LlmAgent + LoopAgent retry)   — vehicle-api-mcp
  │     └── enrich_weather (LlmAgent + LoopAgent retry)   — weather-api-mcp
  ├── severity_classifier (LlmAgent)          — severity_classifier_fn, body-shop-a2a
  └── human_review (CustomAgent / HITL)       — review-queue-mcp
```

DR strategy: Pilot Light — Cold Standby (us-east1 primary, us-west1 DR). 99.95% uptime, RTO 30-60 min, RPO 1 hour.

## Artifact map (the full pipeline, input → output)

| Stage | Artifact | Location | Role |
|---|---|---|---|
| Input | `spec.md` | `inputs/spec.md` | Use case, actors, ordering, data sources, partners, business rules, NFRs |
| Input | `plan.md` | `inputs/plan.md` | Runtime, region, DR strategy, security, observability, CI/CD |
| Output (PRIMARY) | `app-blueprint.md` | `outputs/app-blueprint.md` | 9-section governance document (§1-§9) |
| Output (DERIVED) | `app-blueprint.json` | `outputs/app-blueprint.json` | Machine-readable: adk_agent_tree, tool_bindings, data_flows, infra_modules, business_rules, eval_config, screening_config, pipeline_configs |
| Output (DIAGRAM) | component-topology DSL + .drawio.xml + .png | `diagrams/` | From Eraser.io DSL |
| Output (DIAGRAM) | hadr-lifecycle DSL + .drawio.xml + .png | `diagrams/` | From Eraser.io DSL |
| Reference | Eraser.io DSL examples | `diagrams/fnol-eraser-dsl-examples.md` | Both DSLs, fully worked, showing construction from topology |

## The full template + worked example

The complete `app-blueprint.md` template (all 9 sections with field-level definitions) AND the fully-populated FNOL instance are in:

`templates/blueprint/app-blueprint-template-and-fnol-example.md`

This single file is the most important reference: it shows the template structure, the FNOL instance filling every section, and the mapping of which `.json` fields `assemble_blueprint` derives from which sources.

## How Claude Code should use this

1. **Generating the Solution Accelerator pipeline?** Use the FNOL `spec.md`/`plan.md` as test input and the FNOL `app-blueprint.md`/`.json` as the golden expected output.
2. **Generating the DSL construction (stage 8)?** Use `diagrams/fnol-eraser-dsl-examples.md` as the golden output — given the FNOL topology, the DSL must serialize to match.
3. **Generating accelerator-cli?** Use `outputs/app-blueprint.json` as input; the generated project is the golden tree for the determinism test.
4. **Generating the Governance Guardian?** Use `outputs/app-blueprint.md` §1-§9 as the assessment input fixture.

This example is the end-to-end integration test for the whole platform.

## Note on inputs (authoritative)

`inputs/spec.md` and `inputs/plan.md` are the authoritative FNOL samples extracted from the
Developer Guide appendix (FNOL-T1, FNOL-T2) — the same files the platform documentation ships.
They were authored from `templates/spec/spec-template.md` and `templates/plan/plan-template.md`.

The Solution Accelerator's curated system prompt that reasons over these inputs lives at
`services/solution-accelerator/prompts/greenfield-system-prompt.md` (authored; loaded by
recommend_architecture.py).
