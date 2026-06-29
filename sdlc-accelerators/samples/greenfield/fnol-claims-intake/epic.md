# Rally Epic E4417 — Automated First-Notice-of-Loss (FNOL) intake agent for auto claims

> This is the human-readable view of the Rally Epic that seeds this sample. The coding agent fetches the
> structured payload (`epic.json`) from the **Rally MCP server** during `/accelerator.ingest-epic` —
> credentials stay in the IDE (Entra ID SSO). The Epic is the SOURCE OF REQUIREMENTS; `spec.md` is
> GENERATED from it, then reviewed (not authored from scratch).
>
> **ObjectVersion:** 14 · **Last updated:** 2026-06-22 · Linked: F1201, US3320

## Description
When a customer files an auto claim, the agent first classifies claim severity, then in parallel enriches
the claim from three sources: the policy system, the VIN vehicle service, and the weather service. It
coordinates these enrichment steps and assembles a unified claim record. If a body shop operates their own
estimate system, the agent obtains the estimate from that partner. The agent reads and updates the policy
database and writes the assembled claim to the claims datastore. Route high-severity claims to a human
adjuster for review before finalizing. Loop the enrichment-and-scoring step until the claim-completeness
score is at least 0.9.

## Acceptance Criteria
- End-to-end intake must complete within 5 minutes at the 95th percentile
- Severity classification accuracy must be above 95%
- 100% of high-severity claims are routed to a human adjuster
- No PII is written to logs

## Non-Functional Requirements
- The service must be available 99.9% of the time
- Recovery point objective of 5 minutes and recovery time objective of 30 minutes
- All customer PII must be encrypted at rest and in transit

## Dependencies
- Policy system (transactional, read/write)
- VIN vehicle lookup service
- Body-shop estimate partner (operates their own system)
