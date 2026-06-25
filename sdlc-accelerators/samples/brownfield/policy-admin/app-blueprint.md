# app-blueprint.md — PolicyAdmin-WebForms

> **Archetype:** brownfield-modernization (CSA→TSA)  |  **Lifecycle state:** LIVE  |  **Primary artifact** (you edit this; `app-blueprint.json` is derived).

---

# Part I — Governance (§1–§7)

## §1 Executive Summary
Modernize a legacy .NET WebForms policy-administration application into an Angular SPA + Java Spring Boot service tier on ECS Fargate, preserving the rating contract (now cross-cloud via Apigee) and the external document-print feed.

- **Current host:** vSphere on-prem (DC-West, 6 VMs behind NetScaler)
- **Target:** ECS Fargate microservices + Angular SPA in 522333444555 (policy-prod), us-east-1 (DR us-west-2)
- **Scope:** 4 integrations — INT-001, INT-002, INT-003, INT-004
- **Criticality / Data:** Tier 2 / Confidential (PII)
- **Compliance:** SOX, internal data-protection standard

## §2 Tech Stack
| Layer | Source (CSA) | Target (TSA) |
|---|---|---|
| UI | server-rendered (JSP/WebForms/Struts/Forms) | Angular SPA (CloudFront + S3) |
| Service tier | monolith / WCF / ESB / WebSphere | Spring Boot on ECS Fargate |
| API gateway | on-prem APIC | Apigee (GCP) via PrivateLink→PSC |
| Async | IBM MQ (JMS) | Amazon SQS (AWS SDK) |
| Secrets | various | AWS Secrets Manager |
| IaC | hand-rolled / none | Terraform via company tf-modules |
| CI/CD | Jenkins | Jenkins (TF) + Harness (deploy) |
| Observability | partial | Splunk + Dynatrace + OTel |

## §3 Architecture Decision Log
| ADR | Title | Compliance record |
|---|---|---|
| ADR-019 | Cross-cloud transit via AWS PrivateLink -> GCP PSC (no public egress) | PASS |
| ADR-244 | Enterprise API gateway is Apigee (no AWS API Gateway for domain APIs) | PASS |
| ADR-110 | Cutover strategy must define an automated rollback trigger + procedure | PASS |
| ADR-205 | Tier-1/Tier-2 apps require cross-region DR (primary -> DR region) | PASS |
| ADR-310 | All secrets in AWS Secrets Manager; no secrets in env/AMI/image | PASS |
| ADR-401 | Observability: Splunk logs + Dynatrace APM + OTel traces on every service | PASS |
| ADR-512 | Terraform must reference company tf-modules; no raw aws_* resources | PASS |

_ADR compliance records are produced by the Solution Accelerator's ADR-compliance stage and re-checked by Governance Guardian before generation._

## §4 NFRs
| Category | Requirement |
|---|---|
| Auth | SAML SSO via Ping Federate |
| Authz | RBAC from AD groups |
| Observability | Splunk + Dynatrace + OTel; SLO p95 < 3s |
| DR | Pilot Light (us-east-1 -> us-west-2) |
| RTO/RPO | 4h / 1h |

## §5 Patterns & Service Topology
Target services (one BFF/service per in-scope integration, composed behind CloudFront + ALB):
- **INT-001 → `policy-admin-policy-admin-ui`** — Rewrite; cutover **Big-bang**.
- **INT-002 → `policy-admin-policy-rules-+-service-tier`** — Rewrite; cutover **Strangler-fig**.
- **INT-003 → `policy-admin-rating-service`** — Replatform; cutover **Blue-green**.
- **INT-004 → `policy-admin-document-print-feed`** — Replatform; cutover **Dual-run**.

Cutover patterns in play: Big-bang, Blue-green, Dual-run, Strangler-fig.

## §6 Component Architecture (PNG)
![TSA component architecture](policy-admin-tsa.drawio.png)

_Editable source: `policy-admin-tsa.drawio.xml` (Draw.io / `hediet.vscode-drawio`). Renders the target ECS Fargate services, CloudFront/ALB edge, Apigee cross-cloud path, and SQS._

## §7 HA/DR Views (PNGs)
![DR topology](policy-admin-dr.drawio.png)

_DR strategy: Pilot Light (us-east-1 -> us-west-2); RTO/RPO 4h / 1h (per ADR-205)._

---

# Part II — Technical (§8–§12)

## §8 Integration Decomposition
### INT-001 — Policy admin UI
- **R-Factor:** Rewrite — WebForms postback model cannot be refactored; rebuilt as Angular SPA.
- **Preserve:** same navigation map, same role-gated screens
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** Playwright regression 100%; synthetic p95 < 3s

### INT-002 — Policy rules + service tier
- **R-Factor:** Rewrite — WCF/SOAP -> Spring Boot REST BFF; contract re-expressed as REST.
- **Preserve:** behavioural parity of policy lifecycle transitions; SQL Server retained on-prem (out of scope)
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** transition-parity harness (shadow 7 days, diff < 0.1%)

### INT-003 — Rating service (cross-cloud)
- **R-Factor:** Replatform — Rating consumed via Apigee proxy; contract preserved.
- **Preserve:** same rating OpenAPI v3, same idempotency keys, same cache-fallback semantics
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; cross-cloud call via Apigee (PrivateLink→PSC).
- **Validation gate:** parity validator (shadow 10 days, diff < 0.1%); latency <= +120ms

### INT-004 — Document print feed
- **R-Factor:** Replatform — Scheduled task -> Fargate scheduled job writing to the same SFTP endpoint.
- **Preserve:** same file format, same vendor SFTP endpoint, same nightly SLA
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** 3-night manifest diff = 0; checksum match

## §9 Migration Phases
| Phase | Name | Integrations | Depends on | Gate |
|---|---|---|---|---|
| 0 | Cross-cloud + landing-zone plumbing | — | — | PrivateLink→PSC up; VPC/Secrets ready |
| 1 | Service tier (anchor) | INT-002 | Phase 0 | parity harness green |
| 2 | UI cutover | INT-001 | Phase 1 | UI regression + SLO green |
| 3 | Remaining integrations | INT-003, INT-004 | Phase 1 | per-integration validation |

## §10 Coexistence Constraints
- **INT-002:** BFF -> on-prem SQL Server via VPN (DB retained, +30ms)
- **INT-003:** on-prem rating + Apigee proxy in parallel during soak
- **INT-004:** vendor receives from one source per night (manifest reconciliation)

## §11 IaC Modules (company tf-modules)
| Module | Source | Assigned to |
|---|---|---|
| ecs-fargate-service | github.com/company/tf-modules//ecs-fargate-service?ref=v3.1.0 | all services |
| cloudfront-spa | github.com/company/tf-modules//cloudfront-spa?ref=v2.4.0 | UI |
| sqs-producer | github.com/company/tf-modules//sqs-producer?ref=v3.3.0 | async integration |
| privatelink-psc | github.com/company/tf-modules//privatelink-psc?ref=v1.6.0 | cross-cloud |
| secrets-manager | github.com/company/tf-modules//secrets-manager?ref=v2.2.0 | all |

_Generated Terraform references these modules only — never raw `aws_*` resources (ADR-512)._

## §12 CI/CD & Runtime Compliance
- **Pipeline:** Jenkins (`terraform plan/apply`) → Harness (`policy-admin` blue-green / canary deploy to ECS Fargate). No direct CLI deploy.
- **Refresh gate:** `/accelerator.refresh` checked before deploy; STALE blueprint blocks promotion.
- **Runtime compliance:** AWS Config rules generated from the §3 ADR compliance records (e.g., secrets-in-Secrets-Manager, no-public-egress, encryption-at-rest).
- **Transition artifacts:** feature-flag config (strangler-fig), dual-publish toggle (MQ→SQS), Phase-0 checklist.

