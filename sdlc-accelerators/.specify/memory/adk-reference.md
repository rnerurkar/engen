# ADK Reference — Class Quick Reference

> Loaded into coding agent context during /specify so it reasons about the right constructs.
> NEVER generate ADK code from memory — use the adk-agents skill (Constitution Rule 18).

| Construct | Use |
|---|---|
| SequentialAgent(sub_agents=[...]) | "first... then..." ordering |
| ParallelAgent(sub_agents=[...]) | "in parallel..." |
| LoopAgent(sub_agents=[...], max_iterations=N) | "loop until...", retry |
| LlmAgent(model, tools, before/after_model_callback) | a reasoning agent |
| BaseAgent subclass | HITL / custom control |
| MCPToolset(connection_params) | MCP server tool |
| RemoteA2aAgent(agent_card) | A2A partner agent |
| FunctionTool(func) | IF/THEN business rule |

Adjacency rule: LoopAgent cannot nest directly inside ParallelAgent.
