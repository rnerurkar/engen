> **Lineage:** seeded from Rally Epic `E5103` @ ObjectVersion `11` via `/accelerator.ingest-epic` (see `epic-signal-ledger.json`), then reviewed and completed into this spec.

---
template: sdlc-accelerators-spec
version: "1.0"
archetype: agentic
use_case: loan-underwriting
---

# Agent Specification — Tiered Loan Underwriting

## 1. Business Context
Our retail bank underwrites personal and small-business loans. Loan officers want an agent that takes a loan request and handles it differently depending on size — fast for small loans, thorough for large ones — so that simple loans clear in minutes while large loans get the deeper assessment they need.

## 2. Workflow — Step by Step
The agent first reads the request and determines the loan tier. Then, depending on tier, it does different things:
- For a small loan (≤ $50K): first pull credit, then make an automated decision.
- For a mid-tier loan (> $50K and ≤ $500K): simultaneously collect supporting documents and run risk scoring, then route to a single underwriter for human review.
- For a large loan (> $500K): simultaneously pull multi-bureau credit and run collateral valuation, then refine the risk model repeatedly until the risk score stabilizes, then route to the human credit committee.

The agent coordinates these tier-specific flows and returns a decision package. The words "first... then," "simultaneously," and "refine... until" describe how the work is ordered within each tier.

## 3. Regulatory Requirements
ECOA/Reg B fair-lending. Adverse-action notices within 30 days. SR 11-7 model documentation for the risk model. Every decision and its inputs retained for audit. Financials encrypted at rest, masked in logs. US-only data residency. Records retained 7 years.

## 4. Data Sources
Core banking system (AlloyDB) — read/write — applicant records, loan records, decision packages.
Credit bureau service — read only — multi-bureau credit pulls.
Collateral valuation service — read only — large-loan collateral assessment.

## 5. External Partners & Integrations
KYC/AML screening — partner operates their own system; we send applicant identifiers and receive screening verdicts (A2A).

## 6. What We Own vs What We Connect To
We OWN: the loan coordinator, the tier router, the fast-track flow, the assessment flow, the risk-refinement loop, the decision logic, and the decision-package store.
We CONNECT TO: Core banking (EXISTING AlloyDB), Credit bureau (EXISTING service), Collateral valuation (EXISTING service), KYC/AML (PARTNER, A2A).

## 7. Business Rules
DETERMINE tier FROM loan_amount (small ≤ $50K, mid ≤ $500K, large > $500K)
ON small: PULL credit THEN auto_decide
ON mid: COLLECT documents AND score_risk (together) THEN underwriter_review
ON large: PULL multi_bureau AND value_collateral (together) THEN refine_risk_until_stable THEN credit_committee_review
refine_risk loop EXITS when risk_score delta < 0.02 OR passes >= 5
IF kyc_aml_verdict = "hit" THEN decision = "decline" WITH reason "kyc_aml"

## 8. Transformation Rules
TRANSFORM loan_amount TO USD cents (integer)
TRANSFORM ratios TO 2-decimal float
TRANSFORM dates TO ISO 8601

## 9. Error Handling
IF the credit bureau read fails: hold the request and return "credit_unavailable" (never auto-decide without credit).
IF collateral valuation fails on a large loan: route directly to the credit committee with "collateral_pending".
IF the risk loop does not stabilize by pass 5: return the best estimate with "risk_unstable" for committee review.

## 10. Acceptance Criteria
GIVEN a $30K request WHEN underwritten THEN the fast-track runs (credit → auto-decision) and returns within minutes
GIVEN a $250K request WHEN underwritten THEN documents and risk scoring run together, then an underwriter reviews
GIVEN a $1.2M request WHEN underwritten THEN multi-bureau and collateral run together, the risk model refines until stable, then the committee reviews
GIVEN a KYC/AML hit WHEN screened THEN the decision is "decline" with reason "kyc_aml"
GIVEN the risk loop WHEN inspected THEN it has an explicit exit (delta < 0.02 OR passes >= 5)
