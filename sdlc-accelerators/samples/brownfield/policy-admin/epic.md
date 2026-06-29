# Rally Epic E6106 — a policy administration system on WebLogic 11

*Archetype: brownfield. ObjectVersion 13 · LastUpdate 2026-06-21.*

## Description
a policy administration system on WebLogic 11. all three integrations are in scope. ADF on WebLogic 11. sync api. bidirectional. high. hard-cutover. internal pages. session sticky. 400K sessions/day p95 < 800ms. React SPA on CloudFront. EJB 3 on WebLogic 11. sync api. bidirectional. critical. dual-read. internal REST undocumented. stateful. 1.5M requests/day p95 < 500ms. Spring Boot services on ECS. SOAP client v1 cross-cloud. sync api. read-only. high. dual-read. WSDL documented. stateless. 700K ratings/day p95 < 600ms. Apigee GCP client cross-cloud.

## Non-Functional Requirements
- the service must be available 99.9% of the time
