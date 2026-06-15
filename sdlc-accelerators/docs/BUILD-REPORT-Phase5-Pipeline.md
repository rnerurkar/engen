# Build Report — Phase 5: Provisioning, Scanning, Eval, Deploy Gate

Four components addressing the Harness pipeline / Terraform / scanning / eval gap.
**26 tests passing (8 new), clean lint.**

## #1 — Agent Terraform generation ✅ DONE & TESTED
- `templates/code/agentic-ai-adk/terraform/main.tf.j2` — company modules from infra_modules (Constitution Rule 4)
- `templates/code/agentic-ai-adk/terraform/agents.tf.j2` — per-agent service accounts, least-privilege (Rule 10)
- Renderer extended; `/accelerator.generate` now emits 16 files (was 14): + main.tf + agents.tf
- Validated: zero raw google_*/aws_* resources; delegation-only orchestrators get empty capabilities
- Tested on both FNOL and contract-review blueprints

## #2 — PRS Scanner ✅ DONE & TESTED
- `services/prs-scanner/src/scanner.py` — enforces the constitution rules:
  - Rule 1 (no deploy — catches both shell strings AND subprocess lists via AST)
  - Rule 4 (no raw terraform resources), Rule 5 (no hardcoded secrets)
  - Rule 7 (Model Armor callbacks present on screened agents)
  - Rule 15 (no print()), Rules 11-13/16 (required artifacts exist)
- CLI: `python -m prs_scanner.cli --generated <dir> --blueprint <json>` (exit 1 on CRITICAL)
- Validated: passes clean generated code (0 critical); catches all 4 violation classes on bad code

## #3 — EvalOps harness ✅ gate logic real, SDK call stubbed
- `services/evalops/src/golden_dataset.py` — seeds golden-dataset.json covering every agent (Rule 12)
- `services/evalops/src/eval_runner.py` — Phase-1 gate logic (threshold 0.90); Vertex AI Eval SDK call is the TODO
- Tested: golden seed covers all 8 FNOL agents; gate returns correct exit codes

## #4 — Reference Harness pipeline ✅ scaffold with working gate sequence
- `.harness/pipeline.yaml` — 5 stages in the correct order:
  1. Production Readiness Scan (PRS) → 2. EvalOps Phase 1 Gate → 3. Sign & Attest (cosign + Binary Authorization, NEVER-SWAPPABLE) → 4. Provision Infrastructure (terraform apply, approval-gated) → 5. Deploy to AgentEngine
- `<PLACEHOLDER>` values mark where to wire your Harness connectors, KMS key, attestor, region

## Scope honesty
- #1 and #2 are production-ready, tested code.
- #3's gate logic is real; the Vertex AI Eval SDK scoring call is stubbed (live wiring).
- #4 is a reference pipeline — the stage sequence and gate logic are correct; binding to your live Harness instance, AgentEngine, and connectors is your infra step.
- The platform still never deploys (Constitution Rule 1). This pipeline runs DOWNSTREAM, in your CI/CD, consuming the generated terraform/ + eval/ + the PRS scanner.
