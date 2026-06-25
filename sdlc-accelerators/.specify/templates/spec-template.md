# spec.md — Specification Template

> Filled by the developer via `/speckit.specify`. Captures WHAT to build.
> The Solution Accelerator reads this to infer agent topology, data platform, boundaries, and tools.
> Pattern selection is driven by the natural-language signals below — there is NO separate
> "orchestration style" section. The richer your §2 signals, the higher the confidence.

## §1. Use Case & Actors
<!-- What problem does this solve? Who are the actors (users, systems, partners)?
     If the agent is STARTED by an event (a file landing, a queue message, a schedule) rather than a
     user request, say so here and in §2 — that is the Event-Driven signal. -->

## §2. Workflow Ordering
<!--
  Describe the sequence in plain language, using the signal words below so the Solution Accelerator
  retrieves the right pattern(s) from the 11-pattern catalog. Patterns compose — e.g. a Coordinator
  whose steps include a Parallel fan-out and a Loop with a Critic inside.

  PATTERN SIGNAL CHEAT-SHEET (use the phrasing that matches what actually happens):
    • Sequential pipeline ...... "first… then… finally" (fixed, ordered, dependent steps)
    • Parallel fan-out ......... "simultaneously" / "in parallel" (independent steps at once)
    • Loop / refinement ........ "loop/repeat/refine until <score or condition>" (STATE the threshold)
    • Human-in-the-loop ........ "route to a human" / "requires approval" / "review before finalizing"
    • Coordinator .............. "coordinate across domains" / "delegate to the X, Y, Z agents" then assemble
    • RAG / retrieval .......... "search the <document/knowledge> corpus and reason over it"
    • ReAct (dynamic tools) .... "decide which tool to call based on the result" (agent picks the next
                                  step at runtime — NO fixed order)
    • Event-driven ............. "when <event> occurs" / "triggered by" / "on message" (async start)
    • Supervisor ............... "oversee / monitor / quality-gate the agents and intervene or escalate"
    • Critic / evaluator ....... "validate / score / evaluate / grade the output against <criteria>"
    • Custom tool agent ........ "using our proprietary / internal <model/algorithm>" (owned logic)

  DISAMBIGUATION (say the distinguishing thing explicitly):
    • Coordinator vs Supervisor: delegating work and assembling results = Coordinator; watching other
      agents' output and intervening on quality/escalation = Supervisor.
    • Critic vs Loop: a one-shot "validate/score" step = Critic; "refine until <threshold>" = Loop.
      "refine until the score ≥ 0.9" = a Loop with a Critic inside — write BOTH signals.
    • ReAct vs Sequential: fixed order → ordering words (Sequential); agent picks the next tool from
      what it observes → say so (ReAct).
    • Event-driven WRAPS another pattern: name the trigger AND the handler workflow it starts.

  TIP: mention the data source IN the step where it is used so the tool binds to the right agent. -->

## §3. Scope, Throughput & Latency
<!-- In scope / out of scope. Peak throughput. Latency targets (P95 end-to-end, per-call). -->

## §4. Data Sources
<!-- Each data source the workflow reads/writes. Internal systems → MCP servers.
     Note data classification (PII, Confidential, etc.) and the WORKLOAD TYPE
     (e.g. "BigQuery — analytical, read-only" vs "Cloud SQL — transactional INSERT/UPDATE").
     For knowledge/document retrieval, name it as a CORPUS ("search the policy-document corpus")
     so it reads as a RAG signal, not a transactional query. -->

## §5. External Partners
<!-- Third parties that "operate their own system" → A2A boundaries.
     Note the integration style and trust boundary. "our proprietary / internal <model>" → owned
     logic (FunctionTool, no external connection). You need NOT say MCP vs A2A — API Hub resolves it. -->

## §6. Actors & Permissions
<!-- Who can invoke what. Drives per-agent Workload Identity (IAM) least-privilege derivation —
     each agent gets a dedicated service account scoped to exactly the permissions its tools imply. -->

## §7. Business Rules (IF/THEN)
<!-- Explicit decision rules → FunctionTools. Format: IF <condition> THEN <action>.
     Validation/scoring rules here are ALSO a Critic signal in §2 — e.g.
     "IF completeness_score < 0.9 THEN re-run enrichment" pairs with a "refine until" Loop. -->

## §8. Error Handling & Edge Cases
<!-- Failure modes, retry expectations, fallback behavior. -->

## §9. Non-Functional Requirements
<!-- Availability, recovery (RTO/RPO), performance, security, compliance. -->

## §10. Acceptance Criteria
<!-- Testable conditions that define "done". Seeds the golden dataset. -->
