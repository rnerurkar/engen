# Brownfield Migration Plan — vSphere MPA → AWS SPA

## Migration Strategy (Application-Wide)
- **Overall approach:** strangler-fig with phased cutover; low-risk integrations first, critical last.
- **Cutover sequencing principle:** decouple UI/server (big-bang pair) from API/messaging (independent schedules).

## Per-Integration Decisions

### Integration: INT-001 — UI rendering
- **R-factor:** refactor
- **Cutover strategy:** big-bang
- **Coexistence window:** N/A (paired with INT-002)
- **Phase:** 2
- **Rollback path:** CloudFront origin failback to Tomcat; rollback SLA 15 min
- **Coupling:** INT-002 (cut over together)
- **Context dimensions:** criticality=high, data_size_class=small, messaging_pattern=point-to-point

### Integration: INT-002 — Server-side application logic
- **R-factor:** refactor
- **Cutover strategy:** strangler-fig
- **Coexistence window:** feature-flag dual-read during soak
- **Phase:** 2
- **Rollback path:** feature-flag flip to Tomcat path; rollback SLA 5 min (critical)
- **Coupling:** INT-001
- **Context dimensions:** criticality=tier1, compliance_regime=pci-dss, data_size_class=small

### Integration: INT-003 — Domain API consumption
- **R-factor:** replatform
- **Cutover strategy:** blue-green
- **Coexistence window:** 14-day soak
- **Phase:** 1
- **Rollback path:** gateway route flip APIC↔Apigee; rollback SLA 10 min
- **Coupling:** none (cross-cloud Phase-0 required first)
- **Context dimensions:** criticality=high, region_constraints=cross-cloud, messaging_pattern=point-to-point

### Integration: INT-004 — Async messaging
- **R-factor:** refactor
- **Cutover strategy:** dual-publish
- **Coexistence window:** 48h dual-publish
- **Phase:** 2
- **Rollback path:** disable SQS publish, MQ remains source of truth; rollback SLA 5 min
- **Coupling:** none
- **Context dimensions:** criticality=tier2, messaging_pattern=point-to-point, partner_constraints=downstream-idempotency-48h
