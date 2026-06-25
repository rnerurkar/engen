# Modernization Plan — LoanOrigination-Monolith

## Global Decisions
- **Target AWS account ID:** 633444555666
- **Target region (primary):** us-east-1
- **Target region (DR):** us-west-2
- **Landing zone version:** LZ-2025.3
- **Deployment window approval:** CHG-pending (EA-scheduled change window)

## Per-Integration Decisions

### INT-001 — Applicant portal
- **R-Factor:** Refactor (JSP front-end carved out as a React SPA hitting the new BFF.)
- **Landing zone:** 633444555666 / loan-origination-vpc / private (Fargate)
- **Cutover:** Canary — 5% -> 25% -> 100% over 7 days; auto-rollback if error-rate > 1% or p95 > 4s.
- **Sequencing:** after INT-002 (BFF endpoints first)
- **Coexistence:** SPA + legacy pages co-served behind CloudFront path rules
- **Validation:** canary SLO board green 48h; a11y scan pass

### INT-002 — Origination core
- **R-Factor:** Refactor (Carve application, decisioning, and document modules into Spring Boot services.)
- **Landing zone:** 633444555666 / loan-origination-vpc / private (Fargate)
- **Cutover:** Strangler-fig — Module-by-module strangle via routing facade; rollback re-routes to monolith module.
- **Sequencing:** anchors; before INT-001
- **Coexistence:** anti-corruption layer + outbox to keep monolith DB in sync during strangle
- **Validation:** decision-parity harness (shadow 14 days, mismatch < 0.05%)

### INT-003 — Credit bureau API (cross-cloud)
- **R-Factor:** Replatform (Bureau access proxied via Apigee; contract + consent flow preserved.)
- **Landing zone:** 633444555666 / loan-origination-vpc / private (Fargate)
- **Cutover:** Blue-green — Apigee blue-green; 21-day soak (regulated data); rollback flips to APIC.
- **Sequencing:** after INT-002
- **Coexistence:** APIC + Apigee parallel during soak; single consent ledger
- **Validation:** parity validator (shadow 21 days, diff < 0.05%); consent-audit reconciliation 100%

### INT-004 — Core-banking host link
- **R-Factor:** Retain (Mainframe retained; new services publish to the same MQ via a bridge.)
- **Landing zone:** 633444555666 / loan-origination-vpc / private (Fargate)
- **Cutover:** Dual-publish — New service dual-publishes to MQ for 72h; rollback to monolith publisher.
- **Sequencing:** after INT-002
- **Coexistence:** mainframe consumes from one publisher; dedupe by request_id
- **Validation:** 72h soak; copybook byte-parity 100%; zero dropped bookings

## Cross-Cutting Decisions
- Identity: OIDC via ForgeRock (customers); SAML for staff
- Service auth: mTLS to Apigee (cert in AWS Secrets Manager); Workload Identity / IAM for AWS services
- Secrets: AWS Secrets Manager (per ADR-310)
- Observability: Splunk HEC; Dynatrace OneAgent; OTel sidecar (per ADR-401)
- CI/CD: GitHub Action → Harness `loan-origination` pipeline (no direct deploy)

## Review Status
- [x] Reviewed by: EA Architecture review (sample build)
