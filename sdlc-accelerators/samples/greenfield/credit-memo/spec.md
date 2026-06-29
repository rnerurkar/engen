> **Lineage:** seeded from Rally Epic `E5101` @ ObjectVersion `9` via `/accelerator.ingest-epic` (see `epic-signal-ledger.json`), then reviewed and completed into this spec.

---
template: sdlc-accelerators-spec
version: "1.0"
archetype: agentic
use_case: credit-memo
---

# Agent Specification — Credit Memo Iterative Drafting

## 1. Business Context
Commercial loan officers write a credit memo for committee on every deal. A good memo takes several drafting passes. We want an agent that produces a first draft and then refines that same memo over multiple passes until it reaches a quality bar, rather than handing back a rough first draft.

## 2. Workflow — Step by Step
The agent drafts a credit memo from the deal data, then refines that single stored memo repeatedly: each pass reads the current memo, improves it (tighten the risk narrative, fill gaps, sharpen the recommendation, improve clarity), scores it on a quality rubric, and stores the improved version back. It keeps refining the same memo until the quality score reaches the bar or it hits the pass limit. "Refine... until [quality bar]" describes the loop; there is one memo being progressively improved.

## 3. Regulatory Requirements
SR 11-7 documentation standards for credit analysis. Every memo version retained with its quality score for audit. SOX controls on the lending process. Financials encrypted at rest, masked in logs. US-only data residency. Records retained 7 years.

## 4. Data Sources
Loan origination system (AlloyDB) — read only — deal terms, borrower financials, collateral.
Memo draft store (Firestore) — read/write — the working memo and each refined version.

## 5. External Partners & Integrations
None — all drafting and refinement is in-house.

## 6. What We Own vs What We Connect To
We OWN: the refinement loop, the drafting/refinement agent, the quality rubric scorer, the memo draft store.
We CONNECT TO: Loan origination (EXISTING AlloyDB, read only).

## 7. Business Rules
DRAFT memo FROM deal_data ON pass 1
ON each pass: IMPROVE stored_memo (risk narrative, gaps, recommendation, clarity)
COMPUTE quality_score FROM rubric{completeness, risk_coverage, clarity, recommendation_strength}
IF quality_score >= 0.90 THEN refinement_complete = true
IF pass_count >= 4 THEN stop WITH flag "max_passes_reached"
IF quality_score does not improve across two consecutive passes THEN stop WITH flag "stalled_refinement"

## 8. Transformation Rules
TRANSFORM amounts TO USD cents (integer)
TRANSFORM ratios TO 2-decimal float
TRANSFORM dates TO ISO 8601

## 9. Error Handling
IF the loan-origination read fails: stop before drafting and return "data_unavailable".
IF quality_score does not improve across two consecutive passes: stop and flag "stalled_refinement".
IF pass_count reaches 4 without 0.90: return the best version with "max_passes_reached".

## 10. Acceptance Criteria
GIVEN a complete deal WHEN drafted THEN pass 1 produces a memo and subsequent passes raise quality_score
GIVEN quality_score reaches 0.92 on pass 3 WHEN evaluated THEN the loop exits at pass 3 with refinement_complete
GIVEN quality never reaches 0.90 WHEN pass 4 completes THEN the best memo is returned with "max_passes_reached"
GIVEN quality flat across passes 2 and 3 WHEN detected THEN the loop stops with "stalled_refinement"
GIVEN the loop WHEN inspected THEN it has an explicit exit (score >= 0.90 OR passes >= 4)
