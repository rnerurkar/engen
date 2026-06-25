---
template: sdlc-accelerators-spec
version: "1.0"
archetype: agentic
use_case: order-issue-resolution
---

# Agent Specification — Order Issue Resolution

## 1. Business Context
Our retail support team handles order problems — wrong items, late deliveries, refund requests. We want one agent that handles a customer's order issue end to end, deciding what to check and do next based on what it learns, instead of following a rigid script.

## 2. Workflow — Step by Step
One agent handles the whole interaction. It reads the customer's message, then decides which single tool to use next based on what it has learned so far, looks at the result, and adapts. For example: it may look up the order, see the status is "shipped," then decide to check carrier tracking, see the package is stuck, then decide to offer a replacement or a refund — choosing each tool from the result of the previous step rather than from a fixed order. There is no fan-out and no fixed pipeline; a single agent reasons over its tools until the issue is resolved or escalated.

## 3. Regulatory Requirements
PCI-DSS for any payment/refund handling (no PAN in logs). Consumer-protection refund timelines. Audit trail of every tool call and resolution. PII encrypted at rest, masked in logs. Records retained 3 years.

## 4. Data Sources
Order management system (AlloyDB) — read/write — orders, statuses, resolutions.
Inventory service — read only — stock for replacements.
Payments service — read/write — refunds and goodwill credits.

## 5. External Partners & Integrations
Carrier tracking — read only — live shipment status.
Reverse-logistics partner — operates their own returns system; we hand off return pickups (A2A).

## 6. What We Own vs What We Connect To
We OWN: the resolution agent, the goodwill-credit logic, the order-management store.
We CONNECT TO: Inventory (EXISTING), Payments (EXISTING), Carrier tracking (EXISTING), Reverse logistics (PARTNER, A2A).

## 7. Business Rules
IF order_status = "stuck_in_transit" THEN offer replacement OR refund
IF replacement AND in_stock THEN create replacement order
IF refund THEN process refund via payments
IF goodwill warranted (delay > 5 days) THEN apply goodwill_credit (<= $25)
IF unresolved after 8 reasoning steps OR customer requests human THEN escalate

## 8. Transformation Rules
TRANSFORM amounts TO USD cents (integer)
TRANSFORM tracking_ids TO carrier-normalized form
TRANSFORM timestamps TO ISO 8601

## 9. Error Handling
IF order lookup fails: ask the customer to confirm the order number; do not guess.
IF payments refund fails: create a manual-refund task and tell the customer the timeline.
IF carrier tracking is unavailable: proceed on order-system status and note the gap.

## 10. Acceptance Criteria
GIVEN a "where is my order" message WHEN handled THEN the agent looks up the order, checks tracking, and responds with status or a remedy
GIVEN a stuck shipment WHEN detected THEN the agent offers a replacement (if in stock) or a refund
GIVEN a >5-day delay WHEN resolving THEN the agent applies a goodwill credit ≤ $25
GIVEN no resolution after 8 steps WHEN reached THEN the agent escalates to a human
GIVEN the agent WHEN inspected THEN it is a single reasoning agent selecting tools dynamically (no fixed pipeline)
