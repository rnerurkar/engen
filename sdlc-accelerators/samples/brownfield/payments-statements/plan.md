# Modernization Plan — PaymentsStatements-MainframeFront

## Global Decisions
- **Target AWS account ID:** 744555666777
- **Target region (primary):** us-east-1
- **Target region (DR):** us-west-2
- **Landing zone version:** LZ-2025.3
- **Deployment window approval:** CHG-pending (EA-scheduled change window)

## Per-Integration Decisions

### INT-001 — Statement retrieval API
- **R-Factor:** Replatform (WebSphere MDB -> Spring Boot service calling the same CICS transaction via MQ.)
- **Landing zone:** 744555666777 / payments-statements-vpc / private (Fargate)
- **Cutover:** Strangler-fig — Path flag /api/v1/statements/* to new service; rollback flips flag.
- **Sequencing:** anchors; before INT-002
- **Coexistence:** new service + WebSphere consume same MQ reply queue (correlation id)
- **Validation:** field-level parity (shadow 10 days); PAN-masking audit 100%

### INT-002 — Statement PDF rendering
- **R-Factor:** Refactor (Batch render -> on-demand + scheduled Fargate render service.)
- **Landing zone:** 744555666777 / payments-statements-vpc / private (Fargate)
- **Cutover:** Dual-run — Render both pipelines 5 nights; visual + checksum diff; rollback disables new pipeline.
- **Sequencing:** after INT-001
- **Coexistence:** archive ingests from one pipeline per night
- **Validation:** 5-night checksum match; PDF visual-diff < 0.01%

### INT-003 — Payment posting + fraud (cross-cloud)
- **R-Factor:** Replatform (Fraud scoring consumed via Apigee proxy to GCP; posting preserved.)
- **Landing zone:** 744555666777 / payments-statements-vpc / private (Fargate)
- **Cutover:** Blue-green — Apigee blue-green; 14-day soak; rollback flips to on-prem fraud.
- **Sequencing:** after INT-001
- **Coexistence:** on-prem + GCP fraud parallel; single decision ledger
- **Validation:** parity validator (shadow 14 days, decision diff < 0.05%); latency <= +110ms

### INT-004 — Posting notifications
- **R-Factor:** Refactor (MQ JMS -> SQS via AWS SDK.)
- **Landing zone:** 744555666777 / payments-statements-vpc / private (Fargate)
- **Cutover:** Dual-publish — Dual-publish 48h; rollback to MQ-only if duplicate-rate > 1%.
- **Sequencing:** after INT-003
- **Coexistence:** downstream dedupe by event_id (per ADR-630)
- **Validation:** 24h load test; SQS publish p95 < 50ms

## Cross-Cutting Decisions
- Identity: SAML SSO (staff); mTLS service auth
- Service auth: mTLS to Apigee (cert in AWS Secrets Manager); Workload Identity / IAM for AWS services
- Secrets: AWS Secrets Manager (per ADR-310)
- Observability: Splunk HEC; Dynatrace OneAgent; OTel sidecar (per ADR-401)
- CI/CD: GitHub Action → Harness `payments-statements` pipeline (no direct deploy)

## Review Status
- [x] Reviewed by: EA Architecture review (sample build)
