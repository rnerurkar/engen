> **Lineage:** seeded from Rally Epic `E6106` @ ObjectVersion `13` via `/accelerator.ingest-epic` (see `epic-signal-ledger.json`), then reviewed and completed into this spec.

# Application Modernization Spec

## Application Summary
- **Name:** PolicyAdmin-WebForms
- **Current host:** vSphere on-prem (DC-West, 6 VMs behind NetScaler)
- **Source code repo:** github.company.com/policy/policy-admin-webforms
- **Business criticality:** Tier 2
- **Data classification:** Confidential (PII)
- **Compliance regimes:** SOX, internal data-protection standard

## Modernization Scope
- **Integrations in scope this iteration:** INT-001, INT-002, INT-003, INT-004
- **Integrations explicitly out of scope:** none — full app refactor
- **Target AWS account:** 522333444555 (policy-prod), us-east-1
- **Cross-cloud dependencies:** Apigee on GCP enterprise-apigee-prod (rating API)

## Integration Inventory

### Integration: INT-001 — Policy admin UI

**Functional category:** [x] spa_internal_facing

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS
- Transport: server postbacks (ASPX)
- Auth: Windows Integrated Auth (Kerberos)
- Payload: HTML + ViewState
- Stack: ASP.NET WebForms 4.8, IIS 10
- SLA: p95 < 2.5s, 20 RPS peak
- Criticality: Tier 2
- Failure today: ViewState error -> session loss

**Target Intent**
- Preserve invariants: same navigation map, same role-gated screens
- Acceptable downtime during cutover: 20 min (after-hours)
- Acceptable performance regression: p95 <= 3s first week
- Hard rejections: no postback model

**Dependencies on other integrations:** INT-002

---

### Integration: INT-002 — Policy rules + service tier

**Functional category:** [x] app_to_app_internal

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS SOAP
- Auth: WS-Security, internal AD
- Payload: SOAP/XML (policy.wsdl)
- Stack: .NET WCF 4.8, SQL Server 2017
- SLA: p95 < 800ms, 20 RPS peak
- Criticality: Tier 2
- Failure today: SOAP fault -> UI error banner

**Target Intent**
- Preserve invariants: behavioural parity of policy lifecycle transitions; SQL Server retained on-prem (out of scope)
- Acceptable downtime during cutover: 20 min
- Acceptable performance regression: +75ms p95
- Hard rejections: no business logic in the SPA

**Dependencies on other integrations:** none - anchors cutover

---

### Integration: INT-003 — Rating service (cross-cloud)

**Functional category:** [x] app_to_app_external, [x] app_to_app_cross_cloud, [x] sync_request_response

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS REST
- Auth: API key (header) to on-prem rating engine
- Payload: /docs/rating-v3.openapi.yaml
- Stack: internal rating engine, mTLS
- SLA: p95 < 1.2s, 8 RPS peak
- Criticality: Tier 2
- Failure today: fallback to last-good quote (cached)

**Target Intent**
- Preserve invariants: same rating OpenAPI v3, same idempotency keys, same cache-fallback semantics
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: +120ms p95 cross-cloud
- Hard rejections: no AWS API Gateway (standard is Apigee)

**Dependencies on other integrations:** independent after Apigee provisioned

**Cross-cloud topology:**
- Source: on-prem rating engine, DC-West
- Target: GCP Apigee enterprise-apigee-prod
- Latency budget: 120ms p95 added
- Transit: AWS PrivateLink -> GCP PSC -> Apigee (per ADR-019)

---

### Integration: INT-004 — Document print feed

**Functional category:** [x] app_to_app_external, [x] file_transfer_external

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: SFTP
- Transport: batch file drop to external print vendor
- Auth: SSH key
- Payload: fixed-width + PDF bundle
- Stack: Windows scheduled task + WinSCP
- SLA: nightly batch, 50k docs
- Criticality: Tier 3
- Failure today: retry next window; ops paged on 2nd failure

**Target Intent**
- Preserve invariants: same file format, same vendor SFTP endpoint, same nightly SLA
- Acceptable downtime during cutover: 1 window
- Acceptable performance regression: none
- Hard rejections: no change to vendor contract

**Dependencies on other integrations:** after INT-002

---

## Non-Functional Requirements (Application-Wide)
- Authentication for end users: SAML SSO via Ping Federate
- Authorization model: RBAC from AD groups
- Observability requirements: Splunk + Dynatrace + OTel; SLO p95 < 3s
- DR strategy: Pilot Light (us-east-1 -> us-west-2)
- RTO / RPO: 4h / 1h
