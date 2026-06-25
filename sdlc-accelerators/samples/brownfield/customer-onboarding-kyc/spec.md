# Application Modernization Spec

## Application Summary
- **Name:** CustomerOnboarding-ESB
- **Current host:** On-prem WebSphere ESB + Struts UI (DC-West), 5 nodes
- **Source code repo:** github.company.com/onboarding/customer-onboarding-esb
- **Business criticality:** Tier 1
- **Data classification:** Restricted (PII + KYC)
- **Compliance regimes:** GDPR, SOX, GLBA, BSA/AML

## Modernization Scope
- **Integrations in scope this iteration:** INT-001, INT-002, INT-003, INT-004
- **Integrations explicitly out of scope:** none — full app refactor
- **Target AWS account:** 855666777888 (onboarding-prod), us-east-1
- **Cross-cloud dependencies:** Apigee on GCP enterprise-apigee-prod (sanctions screening)

## Integration Inventory

### Integration: INT-001 — Onboarding UI

**Functional category:** [x] spa_external_facing

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS
- Transport: server-rendered (Struts 2)
- Auth: OIDC via ForgeRock
- Payload: HTML + AJAX
- Stack: Struts 2, Tomcat 8
- SLA: p95 < 2s, 40 RPS peak
- Criticality: Tier 1
- Failure today: save-and-resume; degraded form

**Target Intent**
- Preserve invariants: same OIDC, same save-and-resume, GDPR consent capture, WCAG 2.1 AA
- Acceptable downtime during cutover: 0 min (canary)
- Acceptable performance regression: p95 <= 2.3s
- Hard rejections: no PII in client logs

**Dependencies on other integrations:** INT-002

---

### Integration: INT-002 — KYC orchestration

**Functional category:** [x] app_to_app_internal

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: SOAP/JMS (ESB mediation)
- Auth: WS-Security
- Payload: BPEL flows + canonical XML
- Stack: WebSphere ESB + BPEL
- SLA: p95 < 1.5s, 40 RPS peak
- Criticality: Tier 1
- Failure today: flow suspends; ops resumes

**Target Intent**
- Preserve invariants: same onboarding state machine, same audit + AML hold semantics
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: +90ms p95
- Hard rejections: no ESB; no BPEL

**Dependencies on other integrations:** none - anchors

---

### Integration: INT-003 — Identity verification vendor

**Functional category:** [x] app_to_app_external, [x] sync_request_response

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS REST
- Auth: OAuth2 to vendor
- Payload: /docs/idv-v2.openapi.yaml
- Stack: ESB outbound adapter
- SLA: p95 < 2s, 20 RPS peak
- Criticality: Tier 1
- Failure today: retry; manual review fallback

**Target Intent**
- Preserve invariants: same vendor contract, same data-minimization (GDPR), same retry policy
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: none
- Hard rejections: no change to vendor data-processing agreement

**Dependencies on other integrations:** after INT-002

---

### Integration: INT-004 — Sanctions screening (cross-cloud)

**Functional category:** [x] app_to_app_external, [x] app_to_app_cross_cloud, [x] sync_request_response

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS REST
- Auth: mTLS to on-prem screening
- Payload: /docs/sanctions-v1.openapi.yaml
- Stack: ESB adapter + on-prem screening
- SLA: p95 < 1.8s, 15 RPS peak
- Criticality: Tier 1
- Failure today: fail-closed -> AML hold

**Target Intent**
- Preserve invariants: same screening contract, same fail-closed AML hold, same audit
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: +100ms p95 cross-cloud
- Hard rejections: no AWS API Gateway; screening stays GCP

**Dependencies on other integrations:** independent after Apigee provisioned

**Cross-cloud topology:**
- Source: on-prem screening, DC-West
- Target: GCP Apigee enterprise-apigee-prod -> sanctions screening
- Latency budget: 100ms p95 added
- Transit: AWS PrivateLink -> GCP PSC -> Apigee (per ADR-019)

---

## Non-Functional Requirements (Application-Wide)
- Authentication for end users: OIDC via ForgeRock (customers); SAML for staff
- Authorization model: scope + role claims; AML segregation of duties
- Observability requirements: Splunk + Dynatrace + OTel; GDPR data-minimization in logs; SLO p95 < 2.3s
- DR strategy: Warm Standby (Tier 1, us-east-1 -> us-west-2)
- RTO / RPO: 1h / 5m
