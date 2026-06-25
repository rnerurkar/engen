# Application Modernization Spec

## Application Summary
- **Name:** PaymentsStatements-MainframeFront
- **Current host:** On-prem WebSphere fronting mainframe (DC-East), 4 nodes
- **Source code repo:** github.company.com/payments/statements-service
- **Business criticality:** Tier 1
- **Data classification:** Restricted (PCI + PII)
- **Compliance regimes:** PCI-DSS, SOX, GLBA

## Modernization Scope
- **Integrations in scope this iteration:** INT-001, INT-002, INT-003, INT-004
- **Integrations explicitly out of scope:** none — full app refactor
- **Target AWS account:** 744555666777 (payments-prod), us-east-1
- **Cross-cloud dependencies:** Apigee on GCP enterprise-apigee-prod (fraud scoring)

## Integration Inventory

### Integration: INT-001 — Statement retrieval API

**Functional category:** [x] app_to_app_internal, [x] sync_request_response

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: MQ request/reply
- Transport: IBM MQ to CICS/COBOL (STMT.GET)
- Auth: channel cert
- Payload: copybook -> JSON adapter
- Stack: WebSphere MDB + COBOL
- SLA: p95 < 1.5s, 40 RPS peak
- Criticality: Tier 1
- Failure today: timeout -> retry; cached last statement

**Target Intent**
- Preserve invariants: same statement schema, same masking of PAN, host call retained
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: +80ms p95
- Hard rejections: no PAN in logs or traces

**Dependencies on other integrations:** none - anchors

---

### Integration: INT-002 — Statement PDF rendering

**Functional category:** [x] data_pipeline, [x] app_to_app_internal

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: batch
- Transport: nightly batch render to NAS
- Auth: n/a (internal)
- Payload: AFP -> PDF
- Stack: on-prem batch (Java + AFP toolkit)
- SLA: nightly, 2M docs
- Criticality: Tier 2
- Failure today: rerun window; ops paged

**Target Intent**
- Preserve invariants: byte-equivalent PDF output, same archive path
- Acceptable downtime during cutover: 1 window
- Acceptable performance regression: none
- Hard rejections: no change to archive retention

**Dependencies on other integrations:** after INT-001

---

### Integration: INT-003 — Payment posting + fraud (cross-cloud)

**Functional category:** [x] app_to_app_external, [x] app_to_app_cross_cloud, [x] sync_request_response

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS REST
- Auth: mTLS to on-prem fraud engine
- Payload: /docs/post-v1.openapi.yaml
- Stack: WebSphere REST + fraud SDK
- SLA: p95 < 900ms, 50 RPS peak
- Criticality: Tier 1
- Failure today: fail-closed -> hold for manual review

**Target Intent**
- Preserve invariants: same posting contract, same fail-closed rule, same score thresholds
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: +110ms p95 cross-cloud
- Hard rejections: no AWS API Gateway; fraud stays GCP

**Dependencies on other integrations:** independent after Apigee provisioned

**Cross-cloud topology:**
- Source: on-prem fraud engine, DC-East
- Target: GCP Apigee enterprise-apigee-prod -> fraud scoring
- Latency budget: 110ms p95 added
- Transit: AWS PrivateLink -> GCP PSC -> Apigee (per ADR-019)

---

### Integration: INT-004 — Posting notifications

**Functional category:** [x] app_to_app_internal, [x] event_driven_async

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: JMS
- Transport: IBM MQ (POST.NOTIFY)
- Auth: TLS + channel cert
- Payload: /docs/post-notify-v1.json
- Stack: WebSphere JMS
- SLA: 1000 msg/min, 8000/min peak
- Criticality: Tier 1
- Failure today: backoff; spill to file

**Target Intent**
- Preserve invariants: at-least-once, contract unchanged
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: none
- Hard rejections: no SNS (point-to-point downstream)

**Dependencies on other integrations:** after INT-003

---

## Non-Functional Requirements (Application-Wide)
- Authentication for end users: SAML SSO (staff); mTLS service auth
- Authorization model: RBAC + PCI scope segregation
- Observability requirements: Splunk + Dynatrace + OTel; PAN never logged; SLO p95 < 1.6s
- DR strategy: Warm Standby (Tier 1, us-east-1 -> us-west-2)
- RTO / RPO: 1h / 5m
