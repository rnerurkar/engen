# Rally Epic E6103 — a customer onboarding and KYC application on JBoss 7

*Archetype: brownfield. ObjectVersion 10 · LastUpdate 2026-06-21.*

## Description
a customer onboarding and KYC application on JBoss 7. all three integrations are in scope. Angular 12 on JBoss 7. sync api. bidirectional. high. hard-cutover. internal pages. session sticky. 500K sessions/day p95 < 600ms. SPA on CloudFront. Camunda 7 on JBoss 7. sync api. bidirectional. critical. dual-read. internal REST documented. stateful workflow. 300K cases/day p95 < 900ms. Step Functions on AWS. REST client to vendor v2. sync api. read-only. high. dual-read. OpenAPI 3.0 documented. stateless. 250K verifications/day p95 < 1200ms. API Gateway + Lambda client.

## Non-Functional Requirements
- all applicant PII must be encrypted at rest and in transit
