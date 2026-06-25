---
template: sdlc-accelerators-plan
version: "1.0"
use_case: deal-qualification
---

# Technical Plan — Enterprise Deal Qualification

## Infrastructure
- Runtime: Cloud Run + Agent Engine
- Primary GCP region: us-east4
- DR region: us-central1
- DR strategy: hot-standby
- Database: AlloyDB (deal pipeline)
- Data residency: EU + US (dual region)

## Model Selection
- Primary LLM: gemini-2.0-flash
- Fallback LLM: gemini-2.0-flash-lite

## CI/CD
- Pipeline: Harness (no direct deploy)
- IaC: company Terraform modules via GitHub (github.com/company/terraform-modules)

## Security
- Data classification: confidential (prospect PII)
- Identity: per-agent Workload Identity
- Proxy: Apigee (one route per tool binding)
- PII handling: encrypt at rest (CMEK), mask in logs, VPC-SC, Secret Manager; GDPR lawful-basis tags
- Auth: OAuth 2.1 + Microsoft Entra ID

## Observability
- Dynatrace + Splunk + OTel

## EvalOps
- Evaluation frequency: pre-commit
- HITL reviewers: 1 (sales ops)

## Diagram Tool
- Draw.io (hediet.vscode-drawio); rendered to .png by the Eraser MCP server
