# CLAUDE.md — Governance Guardian MCP Server

> Service-specific context. Read the root `CLAUDE.md` first.

## Role

Independent enterprise-architecture assessment engine. Reads the `app-blueprint.md` (§1-§9 only — NOT the .json, NOT implementation detail) and scores the solution against EA standards. Returns a scorecard + findings. Separate MCP Server from the Solution Accelerator — different ownership (EA team), different lifecycle.

## MCP tools (contracts in `schemas/`)

| Tool | Sync/Async | Contract |
|---|---|---|
| `assess_start(solution_package)` | Async — returns taskId | `schemas/assess_start.json` |
| `assess_status(taskId)` | Sync poll | `schemas/assess_status.json` |
| `assess_result(taskId)` | Sync retrieve | `schemas/assess_result.json` |
| `recordTechDebt(findings)` | Sync | `schemas/record_tech_debt.json` |

## What it reads (the 9 sections)

| § | Section |
|---|---|
| §1 | Application Overview |
| §2 | Component Topology Diagram |
| §3 | Architecture Patterns |
| §4 | Application Tech Stack |
| §5 | DevSecOps Stack |
| §6 | HA/DR Guidance |
| §7 | HA/DR Lifecycle Diagrams |
| §8 | Architecture Decision Log |
| §9 | Non-Functional Requirements |

It does NOT read `app-blueprint.json` — it assesses governance decisions, not implementation.

## Assess-fix-reassess loop

1. `assess_start` → background EA assessment → scorecard + findings
2. Findings classified: **showstopper** (BLOCK) vs **tech debt** (record + resume)
3. Showstoppers: developer fixes .md, re-runs `/accelerator.assess`, iterate until none
4. Tech debt: `recordTechDebt` → emits resume signal + tech_debt_ids (resume signal for code generation)

## CRITICAL — human-authored core

The assessment engine's scoring rubric, the showstopper-vs-tech-debt classification rules, and the per-category EA criteria are **EA-owned IP and human-authored**. Claude Code scaffolds: the MCP server shell, the async task plumbing, the .md section extraction, the scorecard data structures, the recordTechDebt signal flow. Claude Code does NOT invent: the actual assessment logic, scoring weights, or what constitutes a showstopper. Leave those as clearly-marked extension points for the EA team to fill.

## Auth

OAuth 2.1 + Entra ID, same pattern as Solution Accelerator. Scope `sdlc-accelerators.mcp`.

## Tests

Test the extraction (does it correctly parse §1-§9 from a well-formed .md?), the task lifecycle, and the recordTechDebt signal flow. Mock the assessment engine core with a stub that returns fixture scorecards.
