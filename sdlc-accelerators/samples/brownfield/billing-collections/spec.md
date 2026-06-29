> **Lineage:** seeded from Rally Epic `E6101` @ ObjectVersion `12` via `/accelerator.ingest-epic` (see `epic-signal-ledger.json`), then reviewed and completed into this spec.

# Application Modernization Spec

## Application Summary
- **Name:** BillingCollections-Forms
- **Current host:** vSphere on-prem (DC-East), Oracle Forms + PL/SQL batch, 4 VMs
- **Source code repo:** github.company.com/billing/billing-collections-forms
- **Business criticality:** Tier 2
- **Data classification:** Confidential (PII + PCI for stored tokens)
- **Compliance regimes:** PCI-DSS, SOX

## Modernization Scope
- **Integrations in scope this iteration:** INT-001, INT-002, INT-003, INT-004
- **Integrations explicitly out of scope:** none — full app refactor
- **Target AWS account:** 966777888999 (billing-prod), us-east-1
- **Cross-cloud dependencies:** none

## Integration Inventory

### Integration: INT-001 — Billing UI

**Functional category:** [x] spa_internal_facing

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: Oracle Forms runtime
- Transport: Forms applet over HTTPS
- Auth: Oracle SSO
- Payload: Forms messages
- Stack: Oracle Forms 12c, WebLogic
- SLA: p95 < 3s, 15 RPS peak
- Criticality: Tier 2
- Failure today: applet hang -> relaunch

**Target Intent**
- Preserve invariants: same billing screens + role gating
- Acceptable downtime during cutover: 30 min (after-hours)
- Acceptable performance regression: p95 <= 3s
- Hard rejections: no browser plugin / applet

**Dependencies on other integrations:** INT-002

---

### Integration: INT-002 — Collections engine

**Functional category:** [x] data_pipeline, [x] app_to_app_internal

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: in-DB (PL/SQL)
- Transport: scheduled DBMS_SCHEDULER jobs
- Auth: DB roles
- Payload: PL/SQL packages over Oracle 19c
- Stack: PL/SQL batch, Oracle 19c
- SLA: hourly + nightly dunning runs
- Criticality: Tier 2
- Failure today: job rerun; ops paged

**Target Intent**
- Preserve invariants: same dunning rules + aging buckets + ledger postings; Oracle retained on-prem (out of scope)
- Acceptable downtime during cutover: 1 run window
- Acceptable performance regression: +5% run time acceptable
- Hard rejections: no business logic left in DB triggers

**Dependencies on other integrations:** none - anchors

---

### Integration: INT-003 — Payment gateway

**Functional category:** [x] app_to_app_external, [x] sync_request_response

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: HTTPS REST
- Auth: API key + mTLS to external PSP
- Payload: /docs/psp-v2.openapi.yaml (tokenized PAN)
- Stack: PL/SQL + UTL_HTTP
- SLA: p95 < 1.2s, 10 RPS peak
- Criticality: Tier 2
- Failure today: retry; queue for next cycle

**Target Intent**
- Preserve invariants: same PSP contract, tokenization unchanged, PCI scope minimized
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: none
- Hard rejections: no PAN at rest outside the PSP token vault

**Dependencies on other integrations:** after INT-002

---

### Integration: INT-004 — Dunning notifications

**Functional category:** [x] app_to_app_internal, [x] event_driven_async

**Diagram source:** (auto-populated by csa-extractor from the CSA diagram)

**Current State**
- Protocol: JMS
- Transport: IBM MQ (DUN.NOTIFY)
- Auth: TLS + channel cert
- Payload: /docs/dun-notify-v1.json
- Stack: PL/SQL AQ -> MQ bridge
- SLA: 300 msg/min, 3000/min peak
- Criticality: Tier 3
- Failure today: backoff; spill to table

**Target Intent**
- Preserve invariants: at-least-once, contract unchanged
- Acceptable downtime during cutover: 0 min
- Acceptable performance regression: none
- Hard rejections: no SNS

**Dependencies on other integrations:** after INT-002

---

## Non-Functional Requirements (Application-Wide)
- Authentication for end users: SAML SSO via Ping Federate
- Authorization model: RBAC; PCI scope segregation
- Observability requirements: Splunk + Dynatrace + OTel; no PAN in logs; SLO p95 < 3s
- DR strategy: Pilot Light (us-east-1 -> us-west-2)
- RTO / RPO: 4h / 1h
