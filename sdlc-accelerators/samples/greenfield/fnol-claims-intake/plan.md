---
template: sdlc-accelerators-plan
version: "1.0"
use_case: fnol-claims-intake
---

# Technical Plan — Automated FNOL Claims Intake

> Produced from the Epic-ingested `spec.md` (Rally Epic `E2207` @ ObjectVersion 14) after `/specify` review.

## Infrastructure
- Runtime: Cloud Run + Agent Engine
- Primary GCP region: us-east4
- DR region: us-central1
- DR strategy: hot-standby
- Database: AlloyDB (policy DB, read/write) + Firestore (claim intake store)

## Model Selection
- Primary LLM: gemini-2.0-flash
- Fallback LLM: gemini-2.0-flash-lite

## CI/CD
- Pipeline: Harness (no direct deploy)
- IaC: company Terraform modules via GitHub (github.com/company/terraform-modules)

## Security
- Data classification: restricted (PII — claimant + policy data)
- Identity: per-agent Workload Identity
- Proxy: Apigee (one route per tool binding)
- PII handling: encrypt at rest (CMEK), mask in logs, VPC-SC, Secret Manager
- Auth: OAuth 2.1 + Microsoft Entra ID
