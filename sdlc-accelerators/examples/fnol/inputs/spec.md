---
template: sdlc-accelerators-spec
version: "2.0"
archetype: agentic
use_case: fnol-claims-intake
---

# Agent Specification — FNOL Claims Intake

## 1. Business Context
Our auto insurance company processes approximately 2,000 first notice of loss (FNOL) claims per day. Currently, claims intake is handled by call center agents who manually enter data into a legacy mainframe system, look up policy details in a separate application, and classify severity using a paper decision tree. Average handling time is 45 minutes per claim. We want to build an AI agent that automates the intake process, reducing handling time to under 5 minutes while improving data accuracy and consistency.

## 2. Workflow — Step by Step
First, the customer calls or submits a claim through our web portal. The system extracts claimant details (name, policy number, date of loss, description of incident).

Then, in parallel, it enriches from three sources:
- Policy details from the policy management system (coverage limits, deductible, named drivers)
- Vehicle details from the vehicle registry (make, model, year, VIN, market value)
- Weather conditions at the time and location of the incident from weather.gov

After enrichment, the system classifies the claim severity (critical, high, medium, low) based on damage amount, injury reports, and vehicle total loss indicators.

Loop until the quality score exceeds 0.85: validate all enriched data for completeness and consistency.

Route high-severity and critical claims to a human adjuster for review before finalizing. Low and medium severity claims are auto-approved.

Finally, send confirmation notification to the claimant with their claim number and next steps.

## 3. Regulatory Requirements
- All claim data must be retained for 7 years per state insurance regulations
- PII (name, SSN, policy number) must be encrypted at rest and masked in logs
- Audit trail required for every claim status change
- Data residency: US only (us-east1, us-west1)

## 4. Data Systems
- Claims database (Cloud SQL) — read/write — stores claim records, status, notes
- Policy management system — read only — existing REST API at policy-api.internal
- Vehicle registry — read only — existing REST API at vehicle-api.internal

## 5. External Partners & Integrations
- Body shop network — they operate their own system. We send severity + vehicle details, they return repair estimates and available appointment slots.
- Weather.gov — public API, no auth required
- Police report system — future integration (Phase 2)

## 6. What We Own vs What We Connect To
- We OWN: Claims database, claim processing logic, severity classification rules
- We CONNECT TO: Policy management system (EXISTING REST API — MUST use these existing endpoints), Vehicle registry (EXISTING REST API), Body shop partner (THEIR system), Weather.gov (public)

## 7. Business Rules
IF injury_reported = true OR vehicle_total_loss = true THEN severity = "critical"
IF damage_amount > 10000 AND injury_reported = false THEN severity = "high"
IF damage_amount > 2500 AND damage_amount <= 10000 THEN severity = "medium"
IF damage_amount <= 2500 THEN severity = "low"

IF severity = "critical" OR severity = "high" THEN route_to = "human_adjuster"
IF severity = "medium" OR severity = "low" THEN route_to = "auto_approve"

IF policy_status != "active" THEN REJECT claim WITH reason = "inactive_policy"
IF date_of_loss > today() THEN REJECT claim WITH reason = "future_date"

TRANSFORM damage_description TO damage_categories USING keyword extraction (fire, flood, collision, theft, vandalism)

## 8. Transformation Rules
TRANSFORM claimant_phone TO E.164 format USING country_code + national_number
TRANSFORM date_of_loss TO ISO 8601 format
TRANSFORM policy_number TO uppercase + zero-padded (12 digits)

## 9. Error Handling
IF policy-api returns 503: retry 3 times with exponential backoff, then escalate to human
IF vehicle-api returns 404: proceed without vehicle enrichment, flag for manual lookup
IF weather.gov times out: proceed without weather data, set weather_enriched = false
IF body-shop-a2a is unreachable: queue the request, retry every 15 minutes for 4 hours

## 10. Acceptance Criteria
GIVEN a new claim with policy number POL-000123456 WHEN the agent processes it THEN it should return severity "medium" and all enrichments populated within 30 seconds
GIVEN a claim with injury_reported = true WHEN classified THEN severity MUST be "critical" and routed to human adjuster
GIVEN an inactive policy WHEN claim submitted THEN the claim MUST be rejected with reason "inactive_policy"
GIVEN a weather.gov timeout WHEN processing THEN the claim should complete with weather_enriched = false and no error
GIVEN 100 concurrent claims WHEN submitted simultaneously THEN all should complete within 60 seconds with zero data corruption
