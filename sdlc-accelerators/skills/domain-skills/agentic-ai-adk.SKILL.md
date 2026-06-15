# SKILL.md — Domain Skill: Agentic-AI (ADK)

> Domain skill for the **agentic-AI archetype**. Drives `/accelerator.generate` to turn an
> `app-blueprint.json` into production-ready Google ADK agent code. This is the FIRST authored
> domain skill — a validatable reference for the remaining archetypes.
>
> Validated against: `examples/fnol/outputs/app-blueprint.json`.

## What this skill generates

Given an `app-blueprint.json` whose `pattern_composition` resolves to an ADK agent tree, this skill
produces a runnable ADK 2.0 application: agent definitions, tool wiring (MCP + A2A + FunctionTools),
Model Armor callbacks, per-agent Agent Identity, and the runtime entrypoint.

## Inputs (from app-blueprint.json)

| JSON field | Drives |
|---|---|
| `adk_agent_tree` | Agent classes, hierarchy, types (Sequential/Parallel/Loop/LlmAgent/Custom) |
| `tool_bindings[]` | MCP client wiring, A2A clients, FunctionTool registration |
| `business_rules[]` | FunctionTool bodies (IF/THEN logic) |
| `agent_identity_config[]` | Per-agent service account + capability/denied lists |
| `screening_config` | Model Armor input/output callbacks per agent |
| `observability_config` | OTel span instrumentation |
| `data_flows[]` | Inter-agent state passing |

## Type → ADK mapping (deterministic)

| JSON `type` | ADK construct | Template |
|---|---|---|
| `SequentialAgent` | `SequentialAgent(sub_agents=[...])` | `agent_sequential.py.j2` |
| `ParallelAgent` | `ParallelAgent(sub_agents=[...])` | `agent_parallel.py.j2` |
| `LlmAgent` | `LlmAgent(model=..., tools=[...])` | `agent_llm.py.j2` |
| `LlmAgent` + `retry.type=LoopAgent` | `LoopAgent(agent=LlmAgent(...), max_iterations=N)` | `agent_llm.py.j2` (retry block) |
| `CustomAgent` (HITL) | `BaseAgent` subclass with human-review escalation | `agent_hitl.py.j2` |

## Tool binding → wiring (deterministic)

| `tool_bindings[].type` | Generated wiring |
|---|---|
| `mcp_server` | `MCPToolset(connection_params=...)` with endpoint + auth_method |
| `a2a_agent` | `RemoteA2aAgent(agent_card=...)` with endpoint + mTLS |
| `function_tool` | `FunctionTool(func=<generated_fn>)` — body from `business_rules[]` |

## Generation rules (production-readiness requirements)

1. **Every LlmAgent gets Model Armor callbacks** if listed in `screening_config.agents_with_input_screening` / `agents_with_output_screening`. Input screening via `before_model_callback`, output via `after_model_callback`.
2. **Every agent gets an Agent Identity** — the service account and least-privilege capability list from `agent_identity_config[]`. Coordinators are `delegation-only` with all tools `denied`.
3. **Every MCP/A2A call is wrapped** with retry + timeout + structured logging (per root CLAUDE.md).
4. **FunctionTool bodies are generated from `business_rules[]`** — each rule's IF/THEN becomes a branch. Rules sharing `implemented_by` collapse into one function.
5. **OTel spans** wrap every agent invocation, span name from `observability_config`.
6. **No secrets in code** — auth credentials resolved via Secret Manager at runtime.
7. **Deterministic output** — sorted iteration, no timestamps in generated code, stable ordering. Same JSON in → byte-identical out.

## Output layout

```
generated/
  agents/
    <agent_name>.py          — one file per agent in the tree
  tools/
    mcp_clients.py           — MCP toolset wiring
    a2a_clients.py           — A2A client wiring
    function_tools.py        — FunctionTools from business_rules
  callbacks/
    model_armor.py           — input/output screening callbacks
  identity/
    agent_identity.py        — per-agent SA + capability config
  main.py                    — runtime entrypoint, builds + runs the root agent
  requirements.txt
```

## Validation against FNOL

Running this skill on `examples/fnol/outputs/app-blueprint.json` must produce:
- `fnol_coordinator` as a `SequentialAgent` with 4 children (delegation-only identity, all tools denied)
- `parallel_enrichment` as a `ParallelAgent` with 3 `LoopAgent`-wrapped `LlmAgent` children (max 3, exponential)
- `extract_details` with `claims-db-mcp` MCPToolset + `coverage_calculator_fn` FunctionTool
- `severity_classifier` with `severity_classifier_fn` (4 business rules BR-001..BR-004) + `body-shop-a2a` RemoteA2aAgent
- `human_review` as a HITL `BaseAgent` with `review-queue-mcp`
- Model Armor callbacks on all 6 listed agents; output screening on 3
- 6 Agent Identity service accounts

If the generated FNOL app doesn't match this, the skill or templates are wrong.

## What this skill does NOT do

- It does not invent business logic beyond what `business_rules[]` states.
- It does not deploy (the coding agent opens a PR).
- It does not generate eval/promote gates (out of scope — downstream CI/CD).
