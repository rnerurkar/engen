# app-blueprint.md — PaymentsStatements-MainframeFront

> **Archetype:** brownfield-modernization (CSA→TSA)  |  **Lifecycle state:** LIVE  |  **Primary artifact** (you edit this; `app-blueprint.json` is derived).

---

# Part I — Governance (§1–§7)

## §1 Executive Summary
Replatform a mainframe-fronted statements + payment-posting service into containerized Spring Boot APIs on ECS Fargate, preserving the host statement contract, moving PDF rendering off batch, and routing payment posting through cross-cloud fraud scoring.

- **Current host:** On-prem WebSphere fronting mainframe (DC-East), 4 nodes
- **Target:** ECS Fargate microservices + Angular SPA in 744555666777 (payments-prod), us-east-1 (DR us-west-2)
- **Scope:** 4 integrations — INT-001, INT-002, INT-003, INT-004
- **Criticality / Data:** Tier 1 / Restricted (PCI + PII)
- **Compliance:** PCI-DSS, SOX, GLBA

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
| ADR-630 | Async contract changes require at-least-once + downstream dedupe by event_id | PASS |

_ADR compliance records are produced by the Solution Accelerator's ADR-compliance stage and re-checked by Governance Guardian before generation._

## §4 NFRs
| Category | Requirement |
|---|---|
| Auth | SAML SSO (staff); mTLS service auth |
| Authz | RBAC + PCI scope segregation |
| Observability | Splunk + Dynatrace + OTel; PAN never logged; SLO p95 < 1.6s |
| DR | Warm Standby (Tier 1, us-east-1 -> us-west-2) |
| RTO/RPO | 1h / 5m |

## §5 Patterns & Service Topology
Target services (one BFF/service per in-scope integration, composed behind CloudFront + ALB):
- **INT-001 → `payments-statements-statement-retrieval-api`** — Replatform; cutover **Strangler-fig**.
- **INT-002 → `payments-statements-statement-pdf-rendering`** — Refactor; cutover **Dual-run**.
- **INT-003 → `payments-statements-payment-posting-+-fraud`** — Replatform; cutover **Blue-green**.
- **INT-004 → `payments-statements-posting-notifications`** — Refactor; cutover **Dual-publish**.

Cutover patterns in play: Blue-green, Dual-publish, Dual-run, Strangler-fig.

## §6 Component Architecture (PNG)
![TSA component architecture](payments-statements-tsa.drawio.png)

_Editable source: `payments-statements-tsa.drawio.xml` (Draw.io / `hediet.vscode-drawio`). Renders the target ECS Fargate services, CloudFront/ALB edge, Apigee cross-cloud path, and SQS._

## §7 HA/DR Views (PNGs)
![DR topology](payments-statements-dr.drawio.png)

_DR strategy: Warm Standby (Tier 1, us-east-1 -> us-west-2); RTO/RPO 1h / 5m (per ADR-205)._

---

# Part II — Technical (§8–§12)

## §8 Integration Decomposition
### INT-001 — Statement retrieval API
- **R-Factor:** Replatform — WebSphere MDB -> Spring Boot service calling the same CICS transaction via MQ.
- **Preserve:** same statement schema, same masking of PAN, host call retained
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** field-level parity (shadow 10 days); PAN-masking audit 100%

### INT-002 — Statement PDF rendering
- **R-Factor:** Refactor — Batch render -> on-demand + scheduled Fargate render service.
- **Preserve:** byte-equivalent PDF output, same archive path
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** 5-night checksum match; PDF visual-diff < 0.01%

### INT-003 — Payment posting + fraud (cross-cloud)
- **R-Factor:** Replatform — Fraud scoring consumed via Apigee proxy to GCP; posting preserved.
- **Preserve:** same posting contract, same fail-closed rule, same score thresholds
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; cross-cloud call via Apigee (PrivateLink→PSC).
- **Validation gate:** parity validator (shadow 14 days, decision diff < 0.05%); latency <= +110ms

### INT-004 — Posting notifications
- **R-Factor:** Refactor — MQ JMS -> SQS via AWS SDK.
- **Preserve:** at-least-once, contract unchanged
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** 24h load test; SQS publish p95 < 50ms

## §9 Migration Phases
| Phase | Name | Integrations | Depends on | Gate |
|---|---|---|---|---|
| 0 | Cross-cloud + landing-zone plumbing | — | — | PrivateLink→PSC up; VPC/Secrets ready |
| 1 | Service tier (anchor) | INT-001 | Phase 0 | parity harness green |
| 3 | Remaining integrations | INT-002, INT-003, INT-004 | Phase 1 | per-integration validation |

## §10 Coexistence Constraints
- **INT-001:** new service + WebSphere consume same MQ reply queue (correlation id)
- **INT-002:** archive ingests from one pipeline per night
- **INT-003:** on-prem + GCP fraud parallel; single decision ledger
- **INT-004:** downstream dedupe by event_id (per ADR-630)

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
- **Pipeline:** Jenkins (`terraform plan/apply`) → Harness (`payments-statements` blue-green / canary deploy to ECS Fargate). No direct CLI deploy.
- **Refresh gate:** `/accelerator.refresh` checked before deploy; STALE blueprint blocks promotion.
- **Runtime compliance:** AWS Config rules generated from the §3 ADR compliance records (e.g., secrets-in-Secrets-Manager, no-public-egress, encryption-at-rest).
- **Transition artifacts:** feature-flag config (strangler-fig), dual-publish toggle (MQ→SQS), Phase-0 checklist.

