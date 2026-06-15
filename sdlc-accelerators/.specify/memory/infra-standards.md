# Infrastructure Standards

> Loaded during /specify and /plan. Enforced by constitution.md + company-terraform skill.

- Company Terraform modules ONLY — never raw google_*/aws_* (Constitution Rule 4)
- VPC-SC perimeter + CMEK for all data-at-rest (Constitution Rule 8)
- Apigee proxy in front of every endpoint — no public Cloud Run URLs (Constitution Rule 9)
- Per-agent Workload Identity, least-privilege; orchestrators get delegation only (Constitution Rule 10)
- DR strategy from plan.md (Backup&Restore / Pilot Light / Warm Standby)
- Deploy via Jenkins (infra) + Harness (app) — NEVER directly (Constitution Rule 1)
