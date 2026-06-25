You: /accelerator.blueprint

Agent: Blueprint generation started. Checking progress...
Agent: Searching pattern catalog (Workflow ordering words: "first... then", "simultaneously", "refine... until")...
Agent: Discovering integrations in API Hub for core banking, credit bureau, collateral valuation, KYC/AML...
Agent: Searching skill catalog for matching skills...
Agent: LLM reasoning: mapping tools to agents by co-occurrence (credit pull ↔ credit-bureau; collateral ↔ collateral-valuation; KYC/AML ↔ partner A2A)...
Agent: Validating composition (validate_composition)... pattern tree well-formed (LoopAgent not nested in ParallelAgent) ✓
Agent: Assembling blueprint (assemble_blueprint)...
Agent: Blueprint ready! Saved app-blueprint.md + app-blueprint.json + diagrams to your workspace.

Solution Accelerator recommends:
  9 agents: LlmAgent (loan_coordinator), SequentialAgent (fasttrack_intake),
            ParallelAgent (assessment_fanout), LoopAgent (risk_convergence),
            LlmAgent (underwriter_review, HITL) + 4 leaf reasoning agents
  3 MCP servers: core-banking, credit-bureau, collateral-valuation
  1 A2A agent: kyc-aml (partner)
  2 FunctionTools: tier_router, decision_fn  ← YOUR CODE HERE
  2 skills: alloydb v2.1.0, credit-scoring v1.4.0

Review app-blueprint.md (§1–§9) and the assignment audit, then run /accelerator.assess.
Note: tier branching is coordinator-reasoned (LlmAgent + tier_router), not a fixed pipeline.
