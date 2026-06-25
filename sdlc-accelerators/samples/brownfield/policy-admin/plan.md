# Modernization Plan — PolicyAdmin-WebForms

## Global Decisions
- **Target AWS account ID:** 522333444555
- **Target region (primary):** us-east-1
- **Target region (DR):** us-west-2
- **Landing zone version:** LZ-2025.3
- **Deployment window approval:** CHG-pending (EA-scheduled change window)

## Per-Integration Decisions

### INT-001 — Policy admin UI
- **R-Factor:** Rewrite (WebForms postback model cannot be refactored; rebuilt as Angular SPA.)
- **Landing zone:** 522333444555 / policy-admin-vpc / private (Fargate)
- **Cutover:** Big-bang — DNS weighted swap paired with INT-002; rollback to on-prem if P1 in 30 min or p95 > 6s.
- **Sequencing:** after INT-002; simultaneously with INT-002
- **Validation:** Playwright regression 100%; synthetic p95 < 3s

### INT-002 — Policy rules + service tier
- **R-Factor:** Rewrite (WCF/SOAP -> Spring Boot REST BFF; contract re-expressed as REST.)
- **Landing zone:** 522333444555 / policy-admin-vpc / private (Fargate)
- **Cutover:** Strangler-fig — Per-transition feature flags route to new BFF; rollback flips flag off.
- **Sequencing:** anchors; before INT-001
- **Coexistence:** BFF -> on-prem SQL Server via VPN (DB retained, +30ms)
- **Validation:** transition-parity harness (shadow 7 days, diff < 0.1%)

### INT-003 — Rating service (cross-cloud)
- **R-Factor:** Replatform (Rating consumed via Apigee proxy; contract preserved.)
- **Landing zone:** 522333444555 / policy-admin-vpc / private (Fargate)
- **Cutover:** Blue-green — Apigee blue-green; 14-day soak; rollback flips to on-prem endpoint.
- **Sequencing:** after INT-001, INT-002
- **Coexistence:** on-prem rating + Apigee proxy in parallel during soak
- **Validation:** parity validator (shadow 10 days, diff < 0.1%); latency <= +120ms

### INT-004 — Document print feed
- **R-Factor:** Replatform (Scheduled task -> Fargate scheduled job writing to the same SFTP endpoint.)
- **Landing zone:** 522333444555 / policy-admin-vpc / private (Fargate)
- **Cutover:** Dual-run — Run old + new jobs in parallel for 3 nights, compare manifests; rollback disables new job.
- **Sequencing:** after INT-002
- **Coexistence:** vendor receives from one source per night (manifest reconciliation)
- **Validation:** 3-night manifest diff = 0; checksum match

## Cross-Cutting Decisions
- Identity: SAML SSO via Ping Federate
- Service auth: mTLS to Apigee (cert in AWS Secrets Manager); Workload Identity / IAM for AWS services
- Secrets: AWS Secrets Manager (per ADR-310)
- Observability: Splunk HEC; Dynatrace OneAgent; OTel sidecar (per ADR-401)
- CI/CD: GitHub Action → Harness `policy-admin` pipeline (no direct deploy)

## Review Status
- [x] Reviewed by: EA Architecture review (sample build)
