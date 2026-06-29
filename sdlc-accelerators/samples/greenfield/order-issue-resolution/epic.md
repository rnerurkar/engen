# Rally Epic E5104 — Order issue resolution agent

*Archetype: greenfield. ObjectVersion 6 · LastUpdate 2026-06-20.*

## Description
an order-issue-resolution agent for post-purchase support. classify the issue, then in parallel fetch order, shipment, and payment status. escalate refund requests above the auto-approval threshold to a human agent. reads the order management system and writes resolution actions to the case store.

## Acceptance Criteria
- 80% of issues are resolved without human escalation

## Non-Functional Requirements
- the service must be available 99.9% of the time
