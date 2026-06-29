# Rally Epic E6104 — a loan origination monolith on Tomcat 8 lift-and-shifted to EC2

*Archetype: brownfield. ObjectVersion 15 · LastUpdate 2026-06-21.*

## Description
a loan origination monolith on Tomcat 8 lift-and-shifted to EC2. all four integrations are in scope full app refactor. Spring MVC 4 on Tomcat 8. sync api. bidirectional. high. hard-cutover. internal pages. session sticky. 800K sessions/day p95 < 700ms. React SPA on CloudFront. Spring Boot 2 monolith. sync api. bidirectional. critical. dual-read. internal REST documented. stateful. 2M requests/day p95 < 500ms. Spring Boot services on ECS. Apigee client v1 cross-cloud. sync api. read-only. high. dual-read. OpenAPI 3.0 documented. stateless. 600K calls/day p95 < 400ms. Apigee GCP client cross-cloud.

## Non-Functional Requirements
- comply with SOX and GLBA controls
