---
name: brownfield-migration
archetype: brownfield
version: 1.0.0
description: Generate born-safe migration code (Strangler-Fig proxy, message bridge, dual-write window, cutover gate, decommission job) from a brownfield design contract v2.0. Every artifact emits a rollback path and coexistence/cutover telemetry.
---

# Brownfield Migration Generation Skill

Generates migration code per integration, keyed on R-factor + selected transition pattern.

## Mapping: integration type → migration artifact
| Integration type | Cutover strategy | Artifact generated |
|---|---|---|
| sync API | strangler-fig | Strangler-Fig proxy (route old↔new behind a flag) |
| sync API | blue-green | Blue-green gateway switch |
| async messaging | dual-publish | Dual-write window (publish to old + new, downstream idempotency) |
| sync/async | hard-cutover | Cutover gate (guarded switch with rollback) |
| any | retire | Decommission job (safe teardown after soak) |

## Non-negotiable generation rules (constitution)
1. **Every artifact has a rollback path.** No migration code without a documented, tested revert.
2. **Coexistence telemetry is emitted.** Dual-write/dual-read windows publish reconciliation metrics
   the transition diagram references.
3. **No hard-cutover on a bidirectional integration without a dual-write window first.**
4. **No LLM in the artifact body.** Bodies are deterministic templates parameterized by the contract.

## Inputs
- `design_contract.json` (v2.0): tech_substitutions, pattern_selections, migration_phases, attested_adrs.
- Per integration: R-factor, source/target tokens, transition_pattern_ref, coexistence window, rollback path.
