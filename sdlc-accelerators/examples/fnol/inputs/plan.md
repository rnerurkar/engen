---
template: sdlc-accelerators-plan
version: "2.0"
archetype: agentic
use_case: fnol-claims-intake
---

# Technical Plan — FNOL Claims Intake

## Infrastructure
- **Primary GCP region:** us-east1
- **DR region:** us-west1
- **DR strategy:** pilot-cold

## Model Selection
- **Primary LLM:** gemini-2.0-flash
- **Fallback LLM:** gemini-2.0-flash-lite
- **Embedding model:** text-embedding-005

## CI/CD
- **Infrastructure pipeline:** Jenkins
- **Application pipeline:** Harness
- **IaC module source:** github.com/[company]/terraform-modules

## Security
- **Auth method for MCP servers:** mTLS (internal), OAuth 2.1 (policy-api), API Key (vehicle-api)
- **Data classification:** confidential (PII present)
- **PII handling:** encrypt at rest, mask in logs

## Observability
- **APM:** Dynatrace
- **Logging:** Splunk
- **Tracing:** Cloud Trace (default) + Arize Phoenix (eval)

## EvalOps
- **Evaluation frequency:** pre-commit (Phase 1), nightly (Phase 1+2), weekly (all 3 phases)
- **HITL reviewers:** 3
- **AutoSxS baseline model:** gemini-1.5-pro
