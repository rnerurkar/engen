> **Lineage:** seeded from Rally Epic `E5105` @ ObjectVersion `8` via `/accelerator.ingest-epic` (see `epic-signal-ledger.json`), then reviewed and completed into this spec.

---
template: sdlc-accelerators-spec
version: "1.0"
archetype: agentic
use_case: policy-underwriting
---

# Agent Specification — New-Policy Underwriting Risk Assessment

## 1. Business Context
Our P&C insurer underwrites new property policies. We want an agent that runs the independent risk assessments for a new application at the same time and then combines them into one underwriting decision, so applications clear faster.

## 2. Workflow — Step by Step
For each application, the agent simultaneously runs four independent assessments: actuarial pricing, claims-history (with a fraud-signal check), property inspection review, and reinsurance eligibility. They run concurrently because none depends on another. Then it combines the four results into a single underwriting decision package and writes it to policy admin. "Simultaneously" describes the fan-out; "then combine into one decision" describes the synthesis.

## 3. Regulatory Requirements
State insurance regulations and rate-filing compliance. NAIC model audit trail. SIU referral on fraud signals. PII/loss data encrypted at rest, masked in logs. US-only data residency. Records retained 10 years.

## 4. Data Sources
Policy admin system (AlloyDB) — read/write — applications, decision packages.
Claims database — read only — prior loss history.
Inspection store — read only — property inspection reports.

## 5. External Partners & Integrations
Pricing engine — existing internal service — actuarial rating tables.
Reinsurance API — existing internal service — treaty eligibility.
Fraud-signal consortium — operates their own system; we send identifiers and receive a fraud score (A2A).

## 6. What We Own vs What We Connect To
We OWN: the underwriting flow, the four assessment agents, the synthesizer, the decision logic, the policy-admin store.
We CONNECT TO: Pricing engine (EXISTING), Claims DB (EXISTING), Inspection store (EXISTING), Reinsurance API (EXISTING), Fraud consortium (PARTNER, A2A).

## 7. Business Rules
RUN actuarial_pricing AND claims_history AND inspection_review AND reinsurance_check (concurrently)
IF fraud_signal_score >= 0.8 THEN add flag "refer_to_siu"
IF any assessment = "decline" THEN decision = "refer_to_underwriter"
IF all four = "ok" AND price computed THEN decision = "auto_bind_eligible"
IF reinsurance_eligible = false AND coverage_amount > treaty_limit THEN add flag "no_reinsurance"

## 8. Transformation Rules
TRANSFORM coverage_amount TO USD cents (integer)
TRANSFORM rating_factors TO 2-decimal float
TRANSFORM dates TO ISO 8601

## 9. Error Handling
IF one assessment fails: combine the available results and add the matching pending flag; never block on a single branch.
IF inspection is missing: add flag "inspection_pending" and continue.
IF the policy-admin write fails: retry, then queue for manual write.

## 10. Acceptance Criteria
GIVEN a clean application WHEN underwritten THEN all four assessments run concurrently and decision = "auto_bind_eligible"
GIVEN a fraud_signal_score 0.85 WHEN assessed THEN flag "refer_to_siu" is added
GIVEN reinsurance ineligible above treaty limit WHEN assessed THEN flag "no_reinsurance" is added
GIVEN one branch fails WHEN combining THEN available results are used with a pending flag
GIVEN the four assessments WHEN inspected THEN they run concurrently (no inter-dependency)
