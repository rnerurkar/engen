# plan.md — Technical Plan Template

> Filled by the developer via `/speckit.plan`. Captures HOW to build (technical choices).
> The Solution Accelerator reads this for runtime, region, DR, security, observability, CI/CD.

## Runtime
<!-- Cloud Run / Agent Engine. Scaling bounds. -->

## Region & DR Strategy
<!-- Primary region, DR region, DR strategy (Pilot Light / Warm Standby / etc.), RTO/RPO. -->

## Model
<!-- gemini-2.0-flash, etc. Per-agent if different. -->

## Gateway & Security
<!-- Apigee, OAuth 2.1 + Entra ID, VPC-SC, CMEK, Model Armor, Secret Manager. -->

## Observability
<!-- Cloud Monitoring/Logging/Trace defaults; enterprise stack (Dynatrace, Splunk, OTel) if used. -->

## CI/CD
<!-- Cloud Build/Deploy; Jenkins/Harness at runtime. Canary strategy. -->

## EvalOps
<!-- Golden dataset threshold, AutoSxS, Production Readiness Gate. -->

## FinOps
<!-- Cost controls, budget alerts, tagging. -->
