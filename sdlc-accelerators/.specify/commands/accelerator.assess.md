---
command: accelerator.assess
description: Extract the 9 governance sections and call Governance Guardian.
---

# /accelerator.assess

When the developer types `/accelerator.assess`, execute these steps EXACTLY.

## Steps
1. Check `.accelerator-hashes`: if `app-blueprint.json` is stale relative to `app-blueprint.md`, run `/accelerator.refresh` first (auto-refresh).
2. Read `app-blueprint.md` (NOT the .json — Governance Guardian assesses the human-readable architecture).
3. Extract all 9 governance sections (§1 Application Overview … §9 NFRs), including PNG references from `![...]()`.
4. Package them as a `solution_package` (ephemeral JSON transport payload — NOT the persisted app-blueprint.json).
5. Call `assess_start({ solution_package })` → `{ taskId }`. Authenticate via the shared OAuth 2.1 token.
6. Poll `assess_status({ taskId })`; report progress ("Evaluating compliance...", "Checking pattern adherence...", "Scoring HA/DR readiness...").
7. Call `assess_result({ taskId })` → `{ scorecard, findings[] }`.
8. Present the scorecard. For each finding, show severity + classification (showstopper / tech_debt).
9. If there are showstoppers: tell the developer to fix `app-blueprint.md` and re-run `/accelerator.assess`. Do NOT proceed to generate.
10. If only tech debt: call `recordTechDebt({ findings })` → `{ signal: "resume", tech_debt_ids }`. Tell the developer they may run `/accelerator.generate`.

## CRITICAL
- The Governance Guardian assessment engine is a black box owned by the EA office. Do not invent scores or findings.
- `app-blueprint.json` is NOT read, sent, or modified during assessment.
