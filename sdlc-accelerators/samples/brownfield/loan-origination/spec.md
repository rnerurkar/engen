> **Lineage:** seeded from Rally Epic `E6104` @ ObjectVersion `15` via `/accelerator.ingest-epic` (see `epic-signal-ledger.json`), then reviewed and completed into this spec.

# Application Modernization Spec

## Application Summary
- **Name:** LoanOrigination-Monolith
- **Current host:** AWS EC2 (legacy lift-and-shift, 8x m5.2xlarge behind ALB)
- **Source code repo:** github.company.com/lending/loan-origination-monolith
- **Business criticality:** Tier 1
- **Data classification:** Restricted (PII + financial)
- **Compliance regimes:** SOX, GLBA, internal data-protection standard

## Modernization Scope
- **Integrations in scope this iteration:** INT-001, INT-002, INT-003, INT-004
- **Integrations explicitly out of scope:** none — full app refactor
- **Target AWS account:** 633444555666 (lending-prod), us-east-1
- **Cross-cloud dependencies:** Apigee on GCP enterprise-apigee-prod (credit bureau proxy)

## Integration Inventory

### Integration: INT-001 — Applicant portal

**Functional category:** [x] spa_external_facing

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS
- Transport: server-rendered (JSP + jQuery)
- Auth: OIDC via ForgeRock (public customers)
- Payload: HTML + partial AJAX
- Stack: Spring MVC 4 monolith, Tomcat 8.5
- SLA: p95 < 2s, 60 RPS peak
- Criticality: Tier 1
- Failure today: degraded form, save-and-resume

**Target Intent**
- Preserve invariants: same OIDC flow, same save-and-resume, WCAG 2.1 AA
- Acceptable downtime during cutover: 0 min (canary)
- Acceptable performance regression: p95 <= 2.2s
- Hard rejections: no full-page reloads

**Dependencies on other integrations:** INT-002

---

### Integration: INT-002 — Origination core

**Functional category:** [x] app_to_app_internal

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: in-process (monolith modules)
- Auth: internal
- Payload: Java method calls + shared DB
- Stack: Spring 4 monolith, PostgreSQL 12
- SLA: p95 < 700ms, 60 RPS peak
- Criticality: Tier 1
- Failure today: monolith restart, ~3 min recovery

**Target Intent**
- Preserve invariants: decisioning parity (approve/decline/refer), same audit events
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: +60ms p95 during strangle
- Hard rejections: no shared-DB writes across new + old

**Dependencies on other integrations:** none - anchors strangle

---

### Integration: INT-003 — Credit bureau API (cross-cloud)

**Functional category:** [x] app_to_app_external, [x] app_to_app_cross_cloud, [x] sync_request_response

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS REST
- Auth: mTLS + OAuth2 to bureau via on-prem APIC
- Payload: /docs/bureau-v2.openapi.yaml
- Stack: APIC SDK, RestTemplate
- SLA: p95 < 1.5s, 20 RPS peak
- Criticality: Tier 1
- Failure today: circuit breaker -> soft-pull cache, manual review queue

**Target Intent**
- Preserve invariants: same bureau contract, same consent + audit logging, circuit-breaker semantics
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: +100ms p95 cross-cloud
- Hard rejections: no AWS API Gateway (standard is Apigee)

**Dependencies on other integrations:** independent after Apigee provisioned

**Cross-cloud topology:**
- Source: on-prem APIC, DC-East
- Target: GCP Apigee enterprise-apigee-prod
- Latency budget: 100ms p95 added
- Transit: AWS PrivateLink -> GCP PSC -> Apigee (per ADR-019)

---

### Integration: INT-004 — Core-banking host link

**Functional category:** [x] app_to_app_internal, [x] event_driven_async

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: MQ (JMS)
- Transport: IBM MQ to mainframe CICS (LOAN.BOOK.REQ)
- Auth: TLS + channel cert
- Payload: fixed-format copybook
- Stack: Spring JMS + MQ client 9.x
- SLA: 200 msg/min, 2000/min peak
- Criticality: Tier 1
- Failure today: spill-to-file + replay; ops paged

**Target Intent**
- Preserve invariants: exact copybook contract, at-least-once, ordering per account
- Acceptable downtime during cutover: 0 min (dual-publish)
- Acceptable performance regression: none
- Hard rejections: no mainframe changes (out of scope - Retain)

**Dependencies on other integrations:** after INT-002

---

## Non-Functional Requirements (Application-Wide)
- Authentication for end users: OIDC via ForgeRock (customers); SAML for staff
- Authorization model: scope-based + role claims
- Observability requirements: Splunk + Dynatrace + OTel; SLO p95 < 2.2s
- DR strategy: Warm Standby (Tier 1, us-east-1 -> us-west-2)
- RTO / RPO: 1h / 5m
