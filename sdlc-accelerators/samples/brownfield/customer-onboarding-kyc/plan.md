# Modernization Plan — CustomerOnboarding-ESB

## Global Decisions
- **Target AWS account ID:** 855666777888
- **Target region (primary):** us-east-1
- **Target region (DR):** us-west-2
- **Landing zone version:** LZ-2025.3
- **Deployment window approval:** CHG-pending (EA-scheduled change window)

## Per-Integration Decisions

### INT-001 — Onboarding UI
- **R-Factor:** Rewrite (Struts UI rebuilt as Angular SPA against the new BFF.)
- **Landing zone:** 855666777888 / customer-onboarding-kyc-vpc / private (Fargate)
- **Cutover:** Canary — 5% -> 50% -> 100% over 5 days; auto-rollback on error-rate > 1%.
- **Sequencing:** after INT-002
- **Coexistence:** SPA + legacy co-served behind CloudFront path rules
- **Validation:** canary SLO green 48h; consent-capture audit 100%

### INT-002 — KYC orchestration
- **R-Factor:** Rewrite (ESB/BPEL orchestration -> Spring Boot BFF with an explicit state machine.)
- **Landing zone:** 855666777888 / customer-onboarding-kyc-vpc / private (Fargate)
- **Cutover:** Strangler-fig — Per-step flags route to new orchestrator; rollback flips step flags.
- **Sequencing:** anchors; before INT-001
- **Coexistence:** old ESB + new BFF share the case ledger via outbox during strangle
- **Validation:** state-parity harness (shadow 14 days, mismatch < 0.05%)

### INT-003 — Identity verification vendor
- **R-Factor:** Retain (Vendor relationship + contract unchanged; new BFF calls the same endpoint directly.)
- **Landing zone:** 855666777888 / customer-onboarding-kyc-vpc / private (Fargate)
- **Cutover:** Strangler-fig — New BFF adapter behind the same step flag as INT-002; rollback via flag.
- **Sequencing:** after INT-002
- **Coexistence:** one caller per case (ESB or BFF) - no double-charge to vendor
- **Validation:** contract tests green; vendor invoice reconciliation = expected

### INT-004 — Sanctions screening (cross-cloud)
- **R-Factor:** Replatform (Screening consumed via Apigee proxy to GCP; AML semantics preserved.)
- **Landing zone:** 855666777888 / customer-onboarding-kyc-vpc / private (Fargate)
- **Cutover:** Blue-green — Apigee blue-green; 21-day soak (regulated); rollback flips to on-prem.
- **Sequencing:** after INT-002
- **Coexistence:** on-prem + GCP screening parallel; single AML decision ledger
- **Validation:** parity validator (shadow 21 days, decision diff = 0); AML audit reconciliation 100%

## Cross-Cutting Decisions
- Identity: OIDC via ForgeRock (customers); SAML for staff
- Service auth: mTLS to Apigee (cert in AWS Secrets Manager); Workload Identity / IAM for AWS services
- Secrets: AWS Secrets Manager (per ADR-310)
- Observability: Splunk HEC; Dynatrace OneAgent; OTel sidecar (per ADR-401)
- CI/CD: GitHub Action → Harness `customer-onboarding-kyc` pipeline (no direct deploy)

## Review Status
- [x] Reviewed by: EA Architecture review (sample build)
