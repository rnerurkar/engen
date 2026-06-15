# Company Patterns — Naming, Structure, Standards

> Loaded into the coding agent context during /specify.

## Naming conventions
- Agents: snake_case, descriptive (extract_details, severity_classifier)
- Service accounts: sa-{agent-name}@PROJECT.iam.gserviceaccount.com
- Feature branches: feature/{solution-name} (Constitution Rule 2)

## Folder structure (generated project)
```
app/
  agents/        — one file per agent
  tools/         — mcp_clients, a2a_clients, function_tools
  callbacks/     — model_armor
  identity/      — agent_identity
  health.py      — /health + /ready (Constitution Rule 13)
eval/
  golden-dataset.json
config/dynatrace/dashboard.json
terraform/       — company modules only
.pre-commit-config.yaml
.github/workflows/
```

## Coding standards
- Python 3.12, type hints, ruff, pytest, pydantic v2
- Structured JSON logging, never print() (Constitution Rule 15)
- No hardcoded secrets — Secret Manager only (Constitution Rule 5)
