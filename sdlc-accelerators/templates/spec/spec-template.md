# spec.md — Specification Template

> Filled by the developer via `/speckit.specify`. Captures WHAT to build.
> The Solution Accelerator reads this to infer agent topology, data platform, boundaries, and tools.

## §1. Use Case & Actors
<!-- What problem does this solve? Who are the actors (users, systems, partners)? -->

## §2. Workflow Ordering
<!-- Describe the sequence in plain language. Ordering words drive pattern composition:
     "first... then..." → Sequential
     "at the same time / in parallel" → Parallel
     "retry / until success" → Loop
     "human approves / review" → HITL -->

## §3. Scope, Throughput & Latency
<!-- In scope / out of scope. Peak throughput. Latency targets (P95 end-to-end, per-call). -->

## §4. Data Sources
<!-- Each data source the workflow reads/writes. Internal systems → MCP servers.
     Note data classification (PII, Confidential, etc.). -->

## §5. External Partners
<!-- Third parties that "operate their own system" → A2A boundaries.
     Note the integration style and trust boundary. -->

## §6. Actors & Permissions
<!-- Who can invoke what. Drives Agent Identity least-privilege derivation. -->

## §7. Business Rules (IF/THEN)
<!-- Explicit decision rules → FunctionTools. Format: IF <condition> THEN <action>. -->

## §8. Error Handling & Edge Cases
<!-- Failure modes, retry expectations, fallback behavior. -->

## §9. Non-Functional Requirements
<!-- Availability, recovery (RTO/RPO), performance, security, compliance. -->

## §10. Acceptance Criteria
<!-- Testable conditions that define "done". Seeds the golden dataset. -->
