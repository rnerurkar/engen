# Rally Epic E5101 — Iterative credit-memo drafting agent

*Archetype: greenfield. ObjectVersion 9 · LastUpdate 2026-06-20.*

## Description
an iterative credit-memo drafting agent for commercial lending. draft a memo, then progressively improve that same stored memo over multiple passes. exit when the memo meets a quality bar or hits a pass cap. reads loan-origination data and writes memo versions to the memo store.

## Acceptance Criteria
- the memo must reach a quality score of at least 0.90
- no more than 4 refinement passes

## Non-Functional Requirements
- every memo version and score is retained for 7 years
