# Modernization Plan — BillingCollections-Forms

## Global Decisions
- **Target AWS account ID:** 966777888999
- **Target region (primary):** us-east-1
- **Target region (DR):** us-west-2
- **Landing zone version:** LZ-2025.3
- **Deployment window approval:** CHG-pending (EA-scheduled change window)

## Per-Integration Decisions

### INT-001 — Billing UI
- **R-Factor:** Rewrite (Forms applet cannot be refactored; rebuilt as Angular SPA.)
- **Landing zone:** 966777888999 / billing-collections-vpc / private (Fargate)
- **Cutover:** Big-bang — DNS swap paired with INT-002; rollback to Forms if P1 in 30 min.
- **Sequencing:** after INT-002; simultaneously with INT-002
- **Validation:** Playwright regression 100%; synthetic p95 < 3s

### INT-002 — Collections engine
- **R-Factor:** Rewrite (PL/SQL batch -> Spring Boot services + scheduled Fargate jobs.)
- **Landing zone:** 966777888999 / billing-collections-vpc / private (Fargate)
- **Cutover:** Dual-run — Run PL/SQL + new jobs in parallel 5 cycles; ledger diff; rollback disables new jobs.
- **Sequencing:** anchors; before INT-001
- **Coexistence:** ledger written by one engine per cycle (run-token lock)
- **Validation:** 5-cycle ledger parity (diff = 0); aging-bucket reconciliation 100%

### INT-003 — Payment gateway
- **R-Factor:** Retain (PSP relationship + token vault unchanged; new service calls the same PSP endpoint.)
- **Landing zone:** 966777888999 / billing-collections-vpc / private (Fargate)
- **Cutover:** Strangler-fig — New service calls PSP behind INT-002 flag; rollback via flag.
- **Sequencing:** after INT-002
- **Coexistence:** one caller per transaction; idempotency key reused
- **Validation:** PCI scope review pass; contract tests green; settlement reconciliation = expected

### INT-004 — Dunning notifications
- **R-Factor:** Refactor (MQ -> SQS via AWS SDK.)
- **Landing zone:** 966777888999 / billing-collections-vpc / private (Fargate)
- **Cutover:** Dual-publish — Dual-publish 48h; rollback to MQ-only on duplicate-rate > 1%.
- **Sequencing:** after INT-002
- **Coexistence:** downstream dedupe by event_id (per ADR-630)
- **Validation:** 24h load test; SQS publish p95 < 50ms

## Cross-Cutting Decisions
- Identity: SAML SSO via Ping Federate
- Service auth: mTLS to Apigee (cert in AWS Secrets Manager); Workload Identity / IAM for AWS services
- Secrets: AWS Secrets Manager (per ADR-310)
- Observability: Splunk HEC; Dynatrace OneAgent; OTel sidecar (per ADR-401)
- CI/CD: GitHub Action → Harness `billing-collections` pipeline (no direct deploy)

## Review Status
- [x] Reviewed by: EA Architecture review (sample build)
