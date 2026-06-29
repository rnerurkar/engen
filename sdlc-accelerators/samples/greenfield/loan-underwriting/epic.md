# Rally Epic E5103 — Loan underwriting decision agent

*Archetype: greenfield. ObjectVersion 11 · LastUpdate 2026-06-20.*

## Description
a loan-underwriting agent that produces a credit decision recommendation. pull the applicant bureau report and income documents, then assess risk in parallel. route declines and exceptions to a human underwriter. reads the loan-origination system and writes the underwriting decision record.

## Acceptance Criteria
- the underwriting recommendation must complete within 3 minutes at the 95th percentile

## Non-Functional Requirements
- every decision retains its full feature inputs for 7 years for adverse-action audit
