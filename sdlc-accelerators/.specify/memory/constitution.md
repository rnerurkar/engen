# SDLC Accelerators Constitution — Greenfield Agentic Preset
# Version: 2.0 | Effective: 2026-01-01 | Owner: Platform Engineering
# Review cadence: Quarterly with EA office
#
# These rules are ABSOLUTE. The coding agent MUST follow every rule without exception.
# Violation of any rule produces non-compliant output that will fail security review.
# Rules are enforced by: (a) skill constraints, (b) CI/CD pipeline checks, (c) security scan.

# ═══════════════════════════════════════════════════════════════
# SECTION 1: DEPLOYMENT — What you must NEVER do
# ═══════════════════════════════════════════════════════════════

## Rule 1: Never deploy directly
NEVER run `terraform apply`, `kubectl apply`, `docker push`, `gcloud deploy`, or any command
that provisions infrastructure or deploys code to any environment.
- Rationale: All deployments go through Jenkins (infra) + Harness (app) pipelines with approval gates.
- Enforcement: CI/CD pipeline rejects direct deployments. Security scan flags deployment commands in generated scripts.
- Violation example: `subprocess.run(["terraform", "apply"])` in any generated Python file.

## Rule 2: Never push to protected branches
NEVER push to `main`, `master`, `production`, `release/*`, or `hotfix/*` branches.
ALWAYS create feature branches (`feature/{solution-name}`) and open Pull Requests.
- Rationale: PR review + CI pipeline must run before merge.
- Enforcement: Branch protection rules in GitHub. Generated `.github/workflows` must not include push to protected branches.

## Rule 3: Never modify existing systems
NEVER modify existing database schemas, API contracts, shared libraries, or configuration of
systems outside the current project scope. Generate new code alongside existing systems.
- Rationale: Brownfield safety — changes to shared systems require separate change management.
- Enforcement: Code review. Generated Terraform must not reference existing resource IDs for modification.

# ═══════════════════════════════════════════════════════════════
# SECTION 2: INFRASTRUCTURE — How you must build
# ═══════════════════════════════════════════════════════════════

## Rule 4: Always use company Terraform modules
NEVER use raw `google_*` or `aws_*` Terraform resources.
ALWAYS reference company modules from `app-blueprint.json` → `infrastructure.modules[]`.
If no module exists for a required service, add a `# TODO: Request tf-{service} module from platform team`
comment and skip the resource.
- Rationale: Company modules encode security baselines (CMEK, VPC-SC, backup, monitoring) that raw resources lack.
- Enforcement: `company-terraform` overlay skill refuses to generate raw resources. PRS scan for `resource "google_*"`.
- Violation example: `resource "google_cloud_run_service" "agent" { ... }` instead of `module "agent_platform" { source = "github.com/[company]/tf-agentic-pilot-cold" }`.

## Rule 5: Never hardcode secrets
NEVER include API keys, passwords, database connection strings, mTLS certificates,
OAuth client secrets, or any credential in source code, Terraform, config files, or environment variables.
ALWAYS use Google Secret Manager or AWS Secrets Manager with `os.environ["SECRET_NAME"]`.
- Rationale: Hardcoded secrets are the #1 cause of security incidents.
- Enforcement: PRS regex scan for patterns: `AIza...`, `sk-...`, `password=`, `postgresql://user:pass@`, base64 credential blocks.
- Violation example: `STRIPE_KEY = "sk_live_abc123def456"` anywhere in generated code.

## Rule 6: Always use Workload Identity
NEVER use service account key files (`.json` key files).
NEVER use `google.auth.credentials.Credentials(...)` with inline keys.
ALWAYS use `google.auth.default()` (Workload Identity Federation).
- Rationale: Key files can be leaked, rotated incorrectly, or shared insecurely.
- Enforcement: PRS scan for `.json` key files and `Credentials(` with arguments.

# ═══════════════════════════════════════════════════════════════
# SECTION 3: SECURITY — What you must always include
# ═══════════════════════════════════════════════════════════════

## Rule 7: Always generate Model Armor callbacks
For EVERY agent listed in `app-blueprint.json` → `screening_config.agents_with_input_screening[]`,
generate `before_model_callback=model_armor_input_screen`.
For EVERY agent in `screening_config.agents_with_output_screening[]`,
generate `after_model_callback=model_armor_output_screen`.
- Rationale: Model Armor prevents prompt injection (input) and PII leakage (output).
- Enforcement: PRS AST scan checks every LlmAgent constructor for callback registration.
- Violation example: `LlmAgent(name="extract_details", model="gemini-2.0-flash")` without callbacks when agent is in screening_config.

## Rule 8: Always generate VPC-SC and CMEK
ALWAYS generate a VPC-SC perimeter in Terraform enclosing all Cloud Run services, Cloud SQL, and Secret Manager.
ALWAYS generate CMEK encryption keys for all data-at-rest (Cloud SQL, Secret Manager, Cloud Storage).
- Rationale: Enterprise data protection policy — all data encrypted with customer-managed keys, all services behind perimeter.
- Enforcement: PRS HCL scan checks for `google_access_context_manager_service_perimeter` and `google_kms_crypto_key`.

## Rule 9: Never expose endpoints without proxy
NEVER expose Cloud Run service URLs or Agent Engine endpoints directly to the public internet.
ALWAYS route through Apigee proxy with IAM enforcement.
- Rationale: Apigee provides rate limiting, DDoS protection, and audit logging.
- Enforcement: Generated Terraform must set `ingress = "internal-and-cloud-load-balancing"` on Cloud Run.

## Rule 10: Always generate per-agent Workload Identity
For EACH agent in the topology, generate a dedicated GCP service account with IAM bindings
ONLY for the tools assigned to that agent in `app-blueprint.json` → `tools`.
Orchestrator agents get delegation permissions but NO direct data access.
- Rationale: Least-privilege — if one agent is compromised via prompt injection, blast radius is limited.
- Enforcement: PRS HCL scan checks that no agent SA has `roles/owner` or `roles/editor`.

# ═══════════════════════════════════════════════════════════════
# SECTION 4: QUALITY — What you must always generate
# ═══════════════════════════════════════════════════════════════

## Rule 11: Always generate pre-commit eval hook
ALWAYS generate `.pre-commit-config.yaml` with an evaluation hook that runs EvalOps Phase 1
(Vertex AI Eval SDK — automated metrics) on every commit.
- Rationale: Catches quality regressions before they reach the PR.
- Enforcement: PRS file-existence check for `.pre-commit-config.yaml`.

## Rule 12: Always generate golden dataset
ALWAYS generate `eval/golden-dataset.json` seeded from spec §10 acceptance criteria.
Minimum: 10 entries per agent, ≥3 edge cases, ≥1 negative test, 100% agent coverage.
- Rationale: Golden dataset is the quality gate for deployment — without it, EvalOps has nothing to evaluate.
- Enforcement: PRS file-existence + JSON parse + entry count validation.

## Rule 13: Always generate health checks
ALWAYS generate `/health` and `/ready` endpoints in `app/health.py`.
`/health` returns liveness status. `/ready` returns readiness (all dependencies reachable).
- Rationale: Kubernetes/Cloud Run probes require these for auto-restart and traffic routing.
- Enforcement: PRS file-existence check for `app/health.py`.

# ═══════════════════════════════════════════════════════════════
# SECTION 5: OBSERVABILITY — What you must always instrument
# ═══════════════════════════════════════════════════════════════

## Rule 14: Always generate OpenTelemetry spans
Every agent class MUST have `@trace` decorator or `tracer.start_span()` at the entry point.
Span attributes MUST include: `agent.name`, `tool.name`, `llm.model`, `llm.token_count`.
- Rationale: Without spans, latency debugging is impossible in production.
- Enforcement: PRS AST scan checks every LlmAgent for trace instrumentation.

## Rule 15: Always generate structured logging
All log statements MUST use structured JSON format with fields:
`timestamp`, `level`, `agent_name`, `trace_id`, `span_id`, `message`.
NEVER use `print()` statements. ALWAYS use `logging.getLogger(__name__)`.
- Rationale: Splunk ingestion requires structured JSON. Print statements are invisible in production.
- Enforcement: PRS regex scan for `print(` in agent code (excluding test files).

## Rule 16: Always generate Dynatrace dashboard
ALWAYS generate `config/dynatrace/dashboard.json` with tiles for:
agent latency (p50/p95/p99), error rate, throughput, LLM token usage, eval scores.
- Rationale: Day-one observability — ops team needs dashboards from first deployment.
- Enforcement: PRS file-existence check for `config/dynatrace/dashboard.json`.

# ═══════════════════════════════════════════════════════════════
# SECTION 6: CODE GENERATION — How you must generate code
# ═══════════════════════════════════════════════════════════════

## Rule 17: Always read JSON for code generation
ALWAYS read `app-blueprint.json` (the DERIVED, machine-readable artifact) for code generation.
NEVER read `app-blueprint.md` (the PRIMARY, human-readable artifact) during /accelerator.generate.
The `.md` is for human review and Governance Guardian assessment.
The `.json` is for deterministic code generation.
- Rationale: JSON parsing is deterministic. Markdown parsing is fragile and ambiguous.
- Enforcement: `/accelerator.generate` command template (P3) hardcodes JSON path.

## Rule 18: Always follow domain skills
ALWAYS use the `adk-agents` skill for agent class generation (correct constructors, imports, wiring).
ALWAYS use the `adk-tools` skill for tool generation (MCP connections, A2A clients, FunctionTools).
NEVER generate ADK code from memory — the skill encodes the correct patterns.
- Rationale: ADK API evolves. Skills are version-pinned and tested. Memory is stale.
- Enforcement: Skill loading is mandatory in `/accelerator.generate` command template.

## Rule 19: Always follow overlay skills
ALWAYS follow `company-terraform` for infrastructure (company modules, not raw resources).
ALWAYS follow `company-observability` for monitoring (Dynatrace + OTel, not custom).
ALWAYS follow `company-cicd` for pipelines (Jenkins + Harness templates, not custom).
ALWAYS follow `company-security` for security (Model Armor + VPC-SC + CMEK patterns).
- Rationale: Overlay skills encode company standards. Custom infrastructure fails security review.
- Enforcement: Overlay skills are mandatory in `/accelerator.generate` command template.

## Rule 20: Always generate API Hub registration
ALWAYS generate a post-deployment CI/CD step that registers the agent in Apigee API Hub
with `type=a2a_agent`, capabilities from the topology, and an Agent Card URL.
- Rationale: The flywheel — every deployed agent enriches API Hub for future A2A discovery.
- Enforcement: PRS checks for API Hub registration step in pipeline definition.

## Rule 21: Always generate README
ALWAYS generate `README.md` with: project description, architecture summary (from blueprint),
setup instructions, development workflow, deployment instructions (via CI/CD — not direct), and contact info.
- Rationale: Onboarding new developers requires documentation. README is the entry point.
- Enforcement: PRS file-existence check for `README.md`.
