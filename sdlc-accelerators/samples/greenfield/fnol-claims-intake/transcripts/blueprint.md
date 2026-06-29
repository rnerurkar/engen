You: /specify    # review the Epic-ingested spec.md, fill the 3 NEEDS CLARIFICATION sections (§3, §6, §8), then:
You: /plan
You: /accelerator.blueprint

Agent: Blueprint generation started (blueprint_start). Checking progress...
Agent: The Solution Accelerator MCP Server delegates to the Solution Accelerator Agent (ADK).
Agent: Searching pattern catalog (§2 ordering signals: "first classify ... then enrich ... in parallel", "route high-severity ... to a human adjuster")...
Agent: Discovering integrations in API Hub for policy DB, claims history, fraud signals...
Agent: Solution Accelerator Agent · recommend_architecture (LlmAgent) reasoning: classify must precede enrichment (Sequential); three independent reads → Parallel; high-severity → Router + HITL...
Agent: Validating composition (validate_composition)... ParallelAgent branches independent, not nested in a Loop ✓
Agent: Assembling blueprint (assemble_blueprint)...
Agent: Blueprint ready! Saved app-blueprint.md + app-blueprint.json + diagrams to your workspace.

Solution Accelerator recommends:
  7 agents: SequentialAgent (fnol_intake_coordinator), ParallelAgent (claim_enrichment),
            5 LlmAgents (severity_classifier, policy_lookup, claims_history, fraud_signals, adjuster_router)
  3 MCP servers: policy-db (read/write), claims-history (read), fraud-signals (read)
  0 A2A agents
  1 FunctionTool: hitl_escalation_fn  ← YOUR CODE HERE
  3 skills: alloydb v2.1.0, claims-enrichment v1.0.0, severity-rubric v1.1.0

Provenance: this blueprint derives from Rally Epic E2207 @ ObjectVersion 14 (Epic-ingested spec).
Review app-blueprint.md (§1–§9), then run /accelerator.assess.
