---
template: sdlc-accelerators-plan
version: "1.0"
use_case: loan-underwriting
---

# Technical Plan — Tiered Loan Underwriting

## Infrastructure
- Runtime: Cloud Run + Agent Engine
- Primary GCP region: us-east4
- DR region: us-central1
- DR strategy: hot-standby
- Database: AlloyDB (existing core banking)

## Model Selection
- Primary LLM: gemini-2.0-flash
- Fallback LLM: gemini-2.0-flash-lite

## CI/CD
- Pipeline: Harness (provision infra → build per-agent image → deploy → promote Non-Prod → Pre-Prod → Prod → register in API Hub)
- No direct deploy (no agents-cli deploy)
- IaC: company Terraform modules via GitHub (github.com/company/terraform-modules)

## Security
- Data classification: restricted (financial)
- Identity: per-agent Workload Identity (least-privilege from tool bindings)
- Proxy: Apigee (one route per tool binding)
- PII handling: encrypt at rest (CMEK), mask in logs, VPC-SC perimeter, Secret Manager
- Auth: OAuth 2.1 + Microsoft Entra ID

## Observability
- Dynatrace + Splunk + OTel

## EvalOps
- Evaluation frequency: pre-commit
- HITL reviewers: 2 (loan officers)

## Diagram Tool
- Draw.io (hediet.vscode-drawio); rendered to .png by the Eraser MCP server
