# Modernization Plan — ClaimsPortal-MPA

## Global Decisions
- **Target AWS account ID:** 411222333444
- **Target region (primary):** us-east-1
- **Target region (DR):** us-west-2
- **Landing zone version:** LZ-2025.3
- **Deployment window approval:** CHG-pending (EA-scheduled change window)

## Per-Integration Decisions

### INT-001 — UI rendering
- **R-Factor:** Refactor (JSP -> SPA is a different rendering model.)
- **Landing zone:** 411222333444 / claims-portal-mpa-vpc / private (Fargate)
- **Cutover:** Big-bang — Route 53 weighted swap, paired with INT-002; rollback if P1 in 30 min or p95 > 5s.
- **Sequencing:** after INT-002; simultaneously with INT-002
- **Validation:** Selenium suite 100%; synthetic p95 < 2.5s

### INT-002 — Server-side application logic
- **R-Factor:** Refactor (Spring MVC -> Spring Boot BFF on Fargate.)
- **Landing zone:** 411222333444 / claims-portal-mpa-vpc / private (Fargate)
- **Cutover:** Strangler-fig — Feature flag on CloudFront /api/v1/*; rollback if 5xx > 2% or p95 > 1s.
- **Sequencing:** anchors; before INT-001
- **Coexistence:** BFF -> on-prem Oracle (DB retained, +25ms hop)
- **Validation:** API replay 5000 requests, p95 < 600ms

### INT-003 — Domain API consumption
- **R-Factor:** Replatform (APIC SDK -> Apigee SDK, contract preserved.)
- **Landing zone:** 411222333444 / claims-portal-mpa-vpc / private (Fargate)
- **Cutover:** Blue-green — Gateway blue-green; lags INT-001/002 by 14 days soak; rollback flips config to APIC.
- **Sequencing:** after INT-001, INT-002; APIC kept live 30 days
- **Coexistence:** APIC + Apigee live in parallel during soak
- **Validation:** parity validator (shadow 14 days, diff < 0.1%); latency <= +100ms

### INT-004 — Async messaging
- **R-Factor:** Refactor (MQ JMS -> AWS SDK SQS.)
- **Landing zone:** 411222333444 / claims-portal-mpa-vpc / private (Fargate)
- **Cutover:** Dual-publish — Dual-publish for 48h; rollback if duplicate-rate > 1% or missing messages.
- **Sequencing:** after INT-002
- **Coexistence:** downstream deduplicates by event_id (ticket DSN-4471)
- **Validation:** 24h load test; SQS publish p95 < 50ms

## Cross-Cutting Decisions
- Identity: SAML SSO via Ping Federate (Cognito deferred)
- Service auth: mTLS to Apigee (cert in AWS Secrets Manager); Workload Identity / IAM for AWS services
- Secrets: AWS Secrets Manager (per ADR-310)
- Observability: Splunk HEC; Dynatrace OneAgent; OTel sidecar (per ADR-401)
- CI/CD: GitHub Action → Harness `claims-portal-mpa` pipeline (no direct deploy)

## Review Status
- [x] Reviewed by: J. Martinez (EA Architect), reference case
