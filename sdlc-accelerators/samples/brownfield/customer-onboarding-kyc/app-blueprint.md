# app-blueprint.md — CustomerOnboarding-ESB

> **Archetype:** brownfield-modernization (CSA→TSA)  |  **Lifecycle state:** LIVE  |  **Primary artifact** (you edit this; `app-blueprint.json` is derived).

---

# Part I — Governance (§1–§7)

## §1 Executive Summary
Modernize an ESB-orchestrated onboarding flow into an API-first Angular SPA + Spring Boot orchestration BFF, retaining the third-party identity-verification vendor and routing sanctions screening cross-cloud via Apigee, under GDPR + AML controls.

- **Current host:** On-prem WebSphere ESB + Struts UI (DC-West), 5 nodes
- **Target:** ECS Fargate microservices + Angular SPA in 855666777888 (onboarding-prod), us-east-1 (DR us-west-2)
- **Scope:** 4 integrations — INT-001, INT-002, INT-003, INT-004
- **Criticality / Data:** Tier 1 / Restricted (PII + KYC)
- **Compliance:** GDPR, SOX, GLBA, BSA/AML

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
| Auth | OIDC via ForgeRock (customers); SAML for staff |
| Authz | scope + role claims; AML segregation of duties |
| Observability | Splunk + Dynatrace + OTel; GDPR data-minimization in logs; SLO p95 < 2.3s |
| DR | Warm Standby (Tier 1, us-east-1 -> us-west-2) |
| RTO/RPO | 1h / 5m |

## §5 Patterns & Service Topology
Target services (one BFF/service per in-scope integration, composed behind CloudFront + ALB):
- **INT-001 → `customer-onboarding-kyc-onboarding-ui`** — Rewrite; cutover **Canary**.
- **INT-002 → `customer-onboarding-kyc-kyc-orchestration`** — Rewrite; cutover **Strangler-fig**.
- **INT-003 → `customer-onboarding-kyc-identity-verification-vendor`** — Retain; cutover **Strangler-fig**.
- **INT-004 → `customer-onboarding-kyc-sanctions-screening`** — Replatform; cutover **Blue-green**.

Cutover patterns in play: Blue-green, Canary, Strangler-fig.

## §6 Component Architecture (PNG)
![TSA component architecture](customer-onboarding-kyc-tsa.drawio.png)

_Editable source: `customer-onboarding-kyc-tsa.drawio.xml` (Draw.io / `hediet.vscode-drawio`). Renders the target ECS Fargate services, CloudFront/ALB edge, Apigee cross-cloud path, and SQS._

## §7 HA/DR Views (PNGs)
![DR topology](customer-onboarding-kyc-dr.drawio.png)

_DR strategy: Warm Standby (Tier 1, us-east-1 -> us-west-2); RTO/RPO 1h / 5m (per ADR-205)._

---

# Part II — Technical (§8–§12)

## §8 Integration Decomposition
### INT-001 — Onboarding UI
- **R-Factor:** Rewrite — Struts UI rebuilt as Angular SPA against the new BFF.
- **Preserve:** same OIDC, same save-and-resume, GDPR consent capture, WCAG 2.1 AA
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** canary SLO green 48h; consent-capture audit 100%

### INT-002 — KYC orchestration
- **R-Factor:** Rewrite — ESB/BPEL orchestration -> Spring Boot BFF with an explicit state machine.
- **Preserve:** same onboarding state machine, same audit + AML hold semantics
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** state-parity harness (shadow 14 days, mismatch < 0.05%)

### INT-003 — Identity verification vendor
- **R-Factor:** Retain — Vendor relationship + contract unchanged; new BFF calls the same endpoint directly.
- **Preserve:** same vendor contract, same data-minimization (GDPR), same retry policy
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; in-account call.
- **Validation gate:** contract tests green; vendor invoice reconciliation = expected

### INT-004 — Sanctions screening (cross-cloud)
- **R-Factor:** Replatform — Screening consumed via Apigee proxy to GCP; AML semantics preserved.
- **Preserve:** same screening contract, same fail-closed AML hold, same audit
- **Target design:** Spring Boot service on Fargate; contract surface unchanged; cross-cloud call via Apigee (PrivateLink→PSC).
- **Validation gate:** parity validator (shadow 21 days, decision diff = 0); AML audit reconciliation 100%

## §9 Migration Phases
| Phase | Name | Integrations | Depends on | Gate |
|---|---|---|---|---|
| 0 | Cross-cloud + landing-zone plumbing | — | — | PrivateLink→PSC up; VPC/Secrets ready |
| 1 | Service tier (anchor) | INT-002 | Phase 0 | parity harness green |
| 2 | UI cutover | INT-001 | Phase 1 | UI regression + SLO green |
| 3 | Remaining integrations | INT-003, INT-004 | Phase 1 | per-integration validation |

## §10 Coexistence Constraints
- **INT-001:** SPA + legacy co-served behind CloudFront path rules
- **INT-002:** old ESB + new BFF share the case ledger via outbox during strangle
- **INT-003:** one caller per case (ESB or BFF) - no double-charge to vendor
- **INT-004:** on-prem + GCP screening parallel; single AML decision ledger

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
- **Pipeline:** Jenkins (`terraform plan/apply`) → Harness (`customer-onboarding-kyc` blue-green / canary deploy to ECS Fargate). No direct CLI deploy.
- **Refresh gate:** `/accelerator.refresh` checked before deploy; STALE blueprint blocks promotion.
- **Runtime compliance:** AWS Config rules generated from the §3 ADR compliance records (e.g., secrets-in-Secrets-Manager, no-public-egress, encryption-at-rest).
- **Transition artifacts:** feature-flag config (strangler-fig), dual-publish toggle (MQ→SQS), Phase-0 checklist.

