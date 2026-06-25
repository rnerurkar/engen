# Application Modernization Spec

## Application Summary
- **Name:** ClaimsPortal-MPA
- **Current host:** vSphere on-prem (DC-East cluster, 4 VMs behind F5 LTM)
- **Source code repo:** github.company.com/claims/claims-portal-mpa
- **Business criticality:** Tier 2
- **Data classification:** Confidential (PII)
- **Compliance regimes:** SOX, internal data-protection standard

## Modernization Scope
- **Integrations in scope this iteration:** INT-001, INT-002, INT-003, INT-004
- **Integrations explicitly out of scope:** none — full app refactor
- **Target AWS account:** 411222333444 (claims-prod), us-east-1
- **Cross-cloud dependencies:** Apigee on GCP enterprise-apigee-prod

## Integration Inventory

### Integration: INT-001 — UI rendering

**Functional category:** [x] spa_internal_facing

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS
- Transport: server-rendered HTML (JSP)
- Auth: SAML SSO via on-prem Ping Federate (session cookie)
- Payload: HTML pages
- Stack: Tomcat 9 + Spring MVC 5 + JSP
- SLA: p95 < 2s, 30 RPS peak
- Criticality: Tier 2
- Failure today: blank page, full outage

**Target Intent**
- Preserve invariants: same URL paths, same SSO experience
- Acceptable downtime during cutover: 15 min (after-hours)
- Acceptable performance regression: p95 <= 2.5s first week
- Hard rejections: no CSR for /print/* pages

**Dependencies on other integrations:** INT-002

---

### Integration: INT-002 — Server-side application logic

**Functional category:** [x] app_to_app_internal

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS REST
- Auth: SAML session, internal AD
- Payload: JSON (/docs/openapi-v3.yaml)
- Stack: Spring MVC 5, Spring Data JPA, Oracle 19c
- SLA: p95 < 500ms, 30 RPS peak
- Criticality: Tier 2
- Failure today: 5xx to UI

**Target Intent**
- Preserve invariants: same REST contract /api/v1/*, Oracle retained on-prem (out of scope)
- Acceptable downtime during cutover: 15 min (paired with INT-001)
- Acceptable performance regression: +50ms p95
- Hard rejections: no Lambda (sustained traffic)

**Dependencies on other integrations:** none - anchors cutover

---

### Integration: INT-003 — Domain API consumption

**Functional category:** [x] app_to_app_external, [x] app_to_app_cross_cloud, [x] sync_request_response

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS REST
- Auth: OAuth2 client_credentials via APIC, mTLS to APIC edge
- Payload: /docs/domain-api-v2.openapi.yaml
- Stack: Spring RestTemplate, APIC SDK 5.x
- SLA: p95 < 1s, 12 RPS peak
- Criticality: Tier 2
- Failure today: circuit breaker -> cached read-only view

**Target Intent**
- Preserve invariants: same OpenAPI v2, same OAuth flow, same circuit-breaker semantics
- Acceptable downtime during cutover: 0 min (parallel gateway swap)
- Acceptable performance regression: +100ms p95 cross-cloud hop
- Hard rejections: no AWS API Gateway (standard is Apigee)

**Dependencies on other integrations:** independent of INT-001/002 after Apigee provisioned

**Cross-cloud topology:**
- Source: on-prem APIC, DC-East
- Target: GCP Apigee enterprise-apigee-prod
- Latency budget: 100ms p95 added
- Transit: AWS PrivateLink -> GCP PSC -> Apigee (per ADR-019)

---

### Integration: INT-004 — Async messaging

**Functional category:** [x] app_to_app_internal, [x] event_driven_async

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: JMS
- Transport: IBM MQ (CLAIMS.OUT.NOTIFY)
- Auth: TLS + MQ channel cert
- Payload: /docs/notify-event-v1.json
- Stack: Spring JMS + IBM MQ client 9.1
- SLA: 500 msg/min sustained, 5000/min peak
- Criticality: Tier 2
- Failure today: backoff; spill to file + replay after 5 min

**Target Intent**
- Preserve invariants: at-least-once, existing message contract unchanged
- Acceptable downtime during cutover: 0 min (dual-publish covers)
- Acceptable performance regression: none
- Hard rejections: no SNS (downstream wants point-to-point)

**Dependencies on other integrations:** after INT-002 (BFF must exist to publish)

---

## Non-Functional Requirements (Application-Wide)
- Authentication for end users: SAML SSO via Ping Federate (Cognito deferred)
- Authorization model: RBAC from AD groups in SAML assertion
- Observability requirements: Splunk logs, Dynatrace APM, OTel traces; SLO p95 < 2.5s
- DR strategy: Pilot Light (us-east-1 -> us-west-2)
- RTO / RPO: 4h / 1h
