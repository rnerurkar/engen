You: /accelerator.ingest-epic

Agent: Which Rally Epic should I ingest? (FormattedID, e.g. E1234)
You: E4417

Agent: Fetching E4417 from Rally via the Rally MCP server (.vscode/mcp.json — auth via your Entra ID SSO; no credentials leave VS Code)...
Agent: Retrieved Epic E4417 (ObjectVersion 14) — description, 4 acceptance criteria, 3 NFRs, 3 dependencies, 2 linked items.
Agent: Calling ingest_epic on the Solution Accelerator (epic content only — no credentials)...
Agent: Phase A — shaping epic signals (the one LlmAgent → Epic Signal Ledger)...
Agent: Phase B — mapping to spec.md (deterministic; per-section fill-ratio confidence)...
Agent: Done. Wrote spec.md (Rally provenance: E4417 @ ObjectVersion 14) and epic-signal-ledger.json.

Per-section confidence (signal-slot fill ratio):
  §1 Use Case & Actors .......... 1.00
  §2 Workflow Ordering .......... 1.00   (Sequential + Parallel + Coordinator + Loop + HITL signals)
  §3 Scope, Throughput & Latency  0.33   ⚠ review — only latency stated
  §4 Data Sources ............... 1.00
  §5 External Partners .......... 1.00   (body-shop "operates their own system" → A2A)
  §6 Actors & Permissions ....... 0.00   ⚠ review — not stated in the Epic
  §7 Business Rules (IF/THEN) ... 1.00
  §8 Error Handling ............. 0.00   ⚠ review — not stated in the Epic
  §9 Non-Functional Reqs ........ 1.00
  §10 Acceptance Criteria ....... 1.00

Agent: Review the ⚠ sections (§3, §6, §8 carry [NEEDS CLARIFICATION]), then run /specify to confirm,
       then /plan and /accelerator.blueprint. The shaping pass is extractive — it did not invent any
       requirement the Epic does not state.

You: (review spec.md, fill §3/§6/§8, then continue)
You: /specify        # quick — structure already populated from the Epic
You: /plan
You: /accelerator.blueprint
