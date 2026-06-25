---
template: sdlc-accelerators-plan
version: "1.0"
use_case: policy-underwriting
---

# Technical Plan — New-Policy Underwriting Risk Assessment

## Infrastructure
- Runtime: Cloud Run + Agent Engine
- Primary GCP region: us-east4
- DR region: us-central1
- DR strategy: hot-standby
- Database: AlloyDB (policy admin)

## Model Selection
- Primary LLM: gemini-2.0-flash
- Fallback LLM: gemini-2.0-flash-lite

## CI/CD
- Pipeline: Harness (no direct deploy)
- IaC: company Terraform modules via GitHub (github.com/company/terraform-modules)

## Security
- Data classification: restricted (PII + loss data)
- Identity: per-agent Workload Identity
- Proxy: Apigee (one route per tool binding)
- PII handling: encrypt at rest (CMEK), mask in logs, VPC-SC, Secret Manager
- Auth: OAuth 2.1 + Microsoft Entra ID

## Observability
- Dynatrace + Splunk + OTel

## EvalOps
- Evaluation frequency: pre-commit
- HITL reviewers: 2 (underwriters)

## Diagram Tool
- Draw.io (hediet.vscode-drawio); rendered to .png by the Eraser MCP server
