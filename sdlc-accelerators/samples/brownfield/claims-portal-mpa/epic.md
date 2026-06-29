# Rally Epic E6102 — a claims portal multi-page application on Tomcat 9

*Archetype: brownfield. ObjectVersion 14 · LastUpdate 2026-06-21.*

## Description
a claims portal multi-page application on Tomcat 9. all three integrations are in scope. JSP on Tomcat 9. sync api. bidirectional. high. hard-cutover. internal pages. session sticky. 2M page views/day p95 < 800ms. SPA on CloudFront. Servlet 4.0 on Tomcat 9. sync api. bidirectional. critical. dual-read. internal REST undocumented. session sticky. 5M requests/day p95 < 500ms. Spring Boot BFF on ECS Fargate. IBM API Connect 10 client. sync api. read-only. high. dual-read. OpenAPI 3.0 documented. stateless. 1M calls/day p95 < 300ms. Apigee client.

## Non-Functional Requirements
- modernize to a cloud-native SPA
