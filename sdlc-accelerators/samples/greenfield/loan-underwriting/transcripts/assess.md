You: /accelerator.assess

Agent: Extracting solution artifacts from workspace...
       ✓ TSA component diagram (component-topology.drawio.xml)
       ✓ HA/DR views (1 view found)
       ✓ NFRs (from app-blueprint.md §9)
       ✓ Architecture Decision Log (4 entries)
       ✓ Tech stack (from app-blueprint.md §4)
       ✓ Patterns used (Sequential, Parallel, Loop, HITL)

       Governance assessment started (Governance Guardian)... converting app-blueprint.md → PDF...
       Evaluating architecture compliance...
       Checking pattern adherence...
       Scoring HA/DR readiness...
       Assessment complete!

       SCORECARD: 74/100 (Grade C)
       🔴 SHOWSTOPPER: F-001 — Risk-refinement loop has no documented termination bound in §6 HA/DR Guidance (availability risk)
       🟠 HIGH: F-002 — AlloyDB DR is single-region in §6 (no cross-region read replica)
       🟡 MEDIUM: F-003 — gemini-2.0-flash-lite fallback not on the approved model radar

       Fix the showstopper and run /accelerator.assess again.

You: (document the loop exit — delta<0.02 OR 5 passes — in §6 and ADR-002; add AlloyDB cross-region replica to §6)
You: /accelerator.assess

Agent: Re-extracting artifacts... assessment started...
       Assessment complete!

       SCORECARD: 89/100 (Grade B+)
       ✓ No showstoppers.
       🟡 MEDIUM: F-003 — model-radar note (will be recorded as tech debt at generate)

       No showstoppers remain. Proceed to /accelerator.generate.
