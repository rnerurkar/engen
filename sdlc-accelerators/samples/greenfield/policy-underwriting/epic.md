# Rally Epic E5105 — Insurance policy underwriting agent

*Archetype: greenfield. ObjectVersion 8 · LastUpdate 2026-06-20.*

## Description
an insurance policy-underwriting agent for new auto policies. validate the application, then in parallel pull driving record, vehicle, and prior-claims data. route high-risk applications to a human underwriter. reads the policy administration system and writes the underwriting decision.

## Acceptance Criteria
- a quote must be produced within 90 seconds at the 95th percentile

## Non-Functional Requirements
- all applicant PII must be encrypted at rest and in transit
