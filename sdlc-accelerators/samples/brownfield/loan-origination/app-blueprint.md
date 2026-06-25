# app-blueprint.md — LoanOrigination-Monolith

> **Archetype:** brownfield-modernization (CSA→TSA)  |  **Lifecycle state:** LIVE  |  **Primary artifact** (you edit this; `app-blueprint.json` is derived).

---

# Part I — Governance (§1–§7)

## §1 Executive Summary
Decompose a Java loan-origination monolith into domain microservices using strangler-fig, preserving the applicant journey, the credit-bureau contract (cross-cloud via Apigee), and the retained mainframe core-banking link.

- **Current host:** AWS EC2 (legacy lift-and-shift, 8x m5.2xlarge behind ALB)
- **Target:** ECS Fargate microservices + Angular SPA in 633444555666 (lending-prod), us-east-1 (DR us-west-2)
- **Scope:** 4 integrations — INT-001, INT-002, INT-003, INT-004
- **Criticality / Data:** Tier 1 / Restricted (PII + financial)
- **Compliance:** SOX, GLBA, internal data-protection standard

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
| Auth | OIDC via ForgeRock (customers); SAML for staff |
| Authz | scope-based + role claims |
| Observability | Splunk + Dynatrace + OTel; SLO p95 < 2.2s |
| DR | Warm Standby (Tier 1, us-east-1 -> us-west-2) |
| RTO/RPO | 1h / 5m |

## §5 Patterns & Service Topology
Target services (one BFF/service per in-scope integration, composed behind CloudFront + ALB):
- **INT-001 → `loan-origination-applicant-portal`** — Refactor; cutover **Canary**.
- **INT-002 → `loan-origination-origination-core`** — Refactor; cutover **Strangler-fig**.
- **INT-003 → `loan-origination-credit-bureau-api`** — Replatform; cutover **Blue-green**.
- **INT-004 → `loan-origination-core-banking-host-link`** — Retain; cutover **Dual-publish**.

Cutover patterns in play: Blue-green, Canary, Dual-publish, Strangler-fig.

## §6 Component Architecture (PNG)
![TSA component architecture](loan-origination-tsa.drawio.png)

_Editable source: `loan-origination-tsa.drawio.xml` (Draw.io / `hediet.vscode-drawio`). Renders the target ECS Fargate services, CloudFront/ALB edge, Apigee cross-cloud path, and SQS._

## §7 HA/DR Views (PNGs)
![DR topology](loan-origination-dr.drawio.png)

_DR strategy: Warm Standby (Tier 1, us-east-1 -> us-west-2); RTO/RPO 1h / 5m (per ADR-205)._

---

# Part II — Technical (§8–§12)

## §8 Integration Decomposition
### INT-001 — Applicant portal
- **R-Factor:** Refactor — JSP front-end carved out as a React SPA hitting the new BFF.
- **Preserve:** same OIDC flow, same save-and-resume, WCAG 2.1 AA
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** canary SLO board green 48h; a11y scan pass

### INT-002 — Origination core
- **R-Factor:** Refactor — Carve application, decisioning, and document modules into Spring Boot services.
- **Preserve:** decisioning parity (approve/decline/refer), same audit events
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** decision-parity harness (shadow 14 days, mismatch < 0.05%)

### INT-003 — Credit bureau API (cross-cloud)
- **R-Factor:** Replatform — Bureau access proxied via Apigee; contract + consent flow preserved.
- **Preserve:** same bureau contract, same consent + audit logging, circuit-breaker semantics
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; cross-cloud call via Apigee (PrivateLink→PSC).
- **Validation gate:** parity validator (shadow 21 days, diff < 0.05%); consent-audit reconciliation 100%

### INT-004 — Core-banking host link
- **R-Factor:** Retain — Mainframe retained; new services publish to the same MQ via a bridge.
- **Preserve:** exact copybook contract, at-least-once, ordering per account
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** 72h soak; copybook byte-parity 100%; zero dropped bookings

## §9 Migration Phases
| Phase | Name | Integrations | Depends on | Gate |
|---|---|---|---|---|
| 0 | Cross-cloud + landing-zone plumbing | — | — | PrivateLink→PSC up; VPC/Secrets ready |
| 1 | Service tier (anchor) | INT-002 | Phase 0 | parity harness green |
| 2 | UI cutover | INT-001 | Phase 1 | UI regression + SLO green |
| 3 | Remaining integrations | INT-003, INT-004 | Phase 1 | per-integration validation |

## §10 Coexistence Constraints
- **INT-001:** SPA + legacy pages co-served behind CloudFront path rules
- **INT-002:** anti-corruption layer + outbox to keep monolith DB in sync during strangle
- **INT-003:** APIC + Apigee parallel during soak; single consent ledger
- **INT-004:** mainframe consumes from one publisher; dedupe by request_id

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
- **Pipeline:** Jenkins (`terraform plan/apply`) → Harness (`loan-origination` blue-green / canary deploy to ECS Fargate). No direct CLI deploy.
- **Refresh gate:** `/accelerator.refresh` checked before deploy; STALE blueprint blocks promotion.
- **Runtime compliance:** AWS Config rules generated from the §3 ADR compliance records (e.g., secrets-in-Secrets-Manager, no-public-egress, encryption-at-rest).
- **Transition artifacts:** feature-flag config (strangler-fig), dual-publish toggle (MQ→SQS), Phase-0 checklist.

