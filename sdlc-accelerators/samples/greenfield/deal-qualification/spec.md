---
template: sdlc-accelerators-spec
version: "1.0"
archetype: agentic
use_case: deal-qualification
---

# Agent Specification — Enterprise Deal Qualification

## 1. Business Context
Our sales team needs to qualify inbound enterprise leads consistently. We want an agent that looks at a lead from several angles at once and produces a single qualify/disqualify recommendation with a confidence and dissent notes, written back to the CRM.

## 2. Workflow — Step by Step
For each lead, the agent simultaneously runs four independent assessments — account research, ICP fit scoring, deal risk analysis, and champion mapping. The four run concurrently because none depends on another's output. Then it combines the four results into a single consensus recommendation (qualify/disqualify) with a confidence score and any dissent, and writes that back to the CRM. "Simultaneously" and "concurrently" describe the fan-out; "then combine into a single recommendation" describes the synthesis.

## 3. Regulatory Requirements
GDPR/CCPA for prospect PII (lawful-basis tracking, deletion on request). SOC 2 audit trail of each assessment's contribution and the final recommendation. Prospect data retained 2 years or until opt-out. EU + US data residency.

## 4. Data Sources
Deal pipeline database (AlloyDB) — read/write — lead records, assessment results, recommendations.
Firmographics service — read only — company size, industry, revenue.
Intent-data service — read only — buying-intent signals.

## 5. External Partners & Integrations
Data-enrichment partner — operates their own enrichment system; we send domains and receive enriched company data (A2A).

## 6. What We Own vs What We Connect To
We OWN: the qualification flow, the four assessment agents, the consensus logic, the pipeline database, the CRM write-back.
We CONNECT TO: Firmographics (EXISTING), Intent data (EXISTING), Data enrichment (PARTNER, A2A).

## 7. Business Rules
RUN account_research AND fit_scoring AND risk_analysis AND champion_mapping (concurrently)
COMPUTE recommendation FROM the four results
IF >= 3 of 4 assessments agree THEN recommendation = majority WITH confidence = high
IF assessments split 2-2 THEN recommendation = "needs_human" WITH confidence = low
WRITE recommendation (with dissent noted) to CRM

## 8. Transformation Rules
TRANSFORM revenue TO USD (integer)
TRANSFORM employee_count TO integer bands
TRANSFORM domains TO normalized lowercase

## 9. Error Handling
IF one assessment fails: combine the remaining results and lower the confidence; never block on a single failure.
IF firmographics is unavailable: proceed with intent + enrichment and flag "partial_firmographics".
IF the CRM write fails: retry, then queue for manual write-back.

## 10. Acceptance Criteria
GIVEN a strong-fit low-risk lead WHEN qualified THEN ≥3 of 4 assessments agree and recommendation = "qualify" (high confidence)
GIVEN a poor-fit lead WHEN qualified THEN ≥3 of 4 agree and recommendation = "disqualify"
GIVEN a 2-2 split WHEN combined THEN recommendation = "needs_human" (low confidence)
GIVEN one assessment fails WHEN combining THEN the remaining results are used and confidence is lowered
GIVEN the four assessments WHEN inspected THEN they run concurrently (no inter-dependency)
