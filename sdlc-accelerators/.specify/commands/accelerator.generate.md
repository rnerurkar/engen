---
command: accelerator.generate
description: Governance gate + skill-activated code generation. NEVER deploy.
---

# /accelerator.generate

When the developer types `/accelerator.generate`, execute these steps EXACTLY.

## Governance gate (run first — STOP conditions)
1. Verify `/accelerator.assess` produced a `resume` signal (no unresolved showstoppers). If not, STOP and tell the developer to assess first.
2. Check `.accelerator-hashes`: if `app-blueprint.json` is stale, STOP and require `/accelerator.refresh` (generate does NOT auto-refresh — Constitution Rule 17 requires a current JSON).

## Load constraints
3. Load `memory/constitution.md`. These 18 rules are ABSOLUTE and cannot be overridden by any skill or developer instruction.

## Generate (read JSON, never MD — Constitution Rule 17)
4. Read `app-blueprint.json` (the DERIVED artifact).
5. Activate the domain skill for the archetype (`adk-agents`, `adk-tools` — Constitution Rule 18). Generate, per the blueprint:
   - Agent classes, MCP/A2A wiring, FunctionTool stubs (logic marked requires_review)
   - Model Armor callbacks (Rule 7), per-agent Workload Identity (Rule 10)
   - VPC-SC + CMEK, Apigee proxy routes (Rules 8-9)
   - Company Terraform modules only (Rule 4)
   - pre-commit eval hook (Rule 11), golden-dataset.json (Rule 12), health endpoints (Rule 13)
   - OTel spans + structured logging (Rules 14-15), Dynatrace dashboard (Rule 16)
6. Create a feature branch `feature/{solution-name}` and open a Pull Request (Rule 2).

## CRITICAL OVERRIDE — DO NOT DEPLOY
- NEVER run `terraform apply`, `kubectl apply`, `docker push`, `gcloud deploy`, or any deploy/provision command (Constitution Rule 1).
- NEVER push to main/master/production/release/* (Rule 2).
- The coding agent's job ends at "PR opened." Deployment goes through Jenkins + Harness with approval gates.
- Report: "Project generated. Review files, write system prompts, then the PR runs CI."
