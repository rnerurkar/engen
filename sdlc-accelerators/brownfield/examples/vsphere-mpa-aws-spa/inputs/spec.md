# Brownfield Migration Spec — vSphere MPA → AWS SPA

## Application Summary
A legacy multi-page application (Java + JSP on Tomcat) runs on vSphere, with two outbound
integrations: a synchronous domain API via IBM API Connect on-prem, and an asynchronous IBM MQ
producer to a queue consumed by a downstream app already in AWS. Business driver: exit the
on-prem datacenter and modernize to a cloud-native SPA.

## Modernization Scope
All four integrations are in scope. INT-001 (UI) and INT-002 (server logic) cut over together;
INT-003 (domain API) and INT-004 (messaging) follow on their own schedules.

## Integration Inventory

### Integration: INT-001 — UI rendering
- **Technology + version:** JSP on Tomcat 9 (server-rendered)
- **Integration type:** sync API
- **Data flow direction:** bidirectional
- **Criticality:** high
- **Coexistence constraint:** hard-cutover
- **API surface / contract:** internal — none (server-rendered pages)
- **State management:** session (sticky)
- **Data volume + SLA:** ~2M page views/day; p95 < 800ms
- **Target intent:** SPA on CloudFront + S3
- **Hard rejections:** none

### Integration: INT-002 — Server-side application logic
- **Technology + version:** Tomcat 9 / Servlet 4.0 (Java 11)
- **Integration type:** sync API
- **Data flow direction:** bidirectional
- **Criticality:** critical
- **Coexistence constraint:** dual-read
- **API surface / contract:** internal REST (undocumented) — to be formalized as BFF OpenAPI
- **State management:** session (sticky)
- **Data volume + SLA:** ~5M requests/day; p95 < 500ms
- **Target intent:** Spring Boot BFF on ECS Fargate
- **Hard rejections:** none

### Integration: INT-003 — Domain API consumption
- **Technology + version:** IBM API Connect 10 client (on-prem)
- **Integration type:** sync API
- **Data flow direction:** read-only
- **Criticality:** high
- **Coexistence constraint:** dual-read
- **API surface / contract:** OpenAPI 3.0 (documented)
- **State management:** stateless
- **Data volume + SLA:** ~1M calls/day; p95 < 300ms
- **Target intent:** Apigee (GCP) client — cross-cloud
- **Hard rejections:** none

### Integration: INT-004 — Async messaging
- **Technology + version:** IBM MQ 9.1 producer (spring-jms)
- **Integration type:** async messaging
- **Data flow direction:** write-only
- **Criticality:** medium
- **Coexistence constraint:** dual-write
- **API surface / contract:** internal — none (message contract documented separately)
- **State management:** stateless
- **Data volume + SLA:** ~500K messages/day; downstream idempotency SLA 48h
- **Target intent:** AWS SQS producer (direct publish)
- **Hard rejections:** none

## Non-Functional Requirements (Application-Wide)
- Availability / DR target: Pilot Light (RTO 4h, RPO 1h)
- Compliance regime: PCI-DSS (cardholder data in INT-002 path)
- Region constraints: us-east-1 primary; GCP us-east4 for Apigee (INT-003)
