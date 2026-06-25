You: /accelerator.assess

Agent: Extracting solution artifacts from workspace...
       ✓ TSA component diagram (component-topology.drawio.xml)
       ✓ HA/DR views (1 view found)
       ✓ NFRs (from app-blueprint.md §9)
       ✓ Architecture Decision Log (4 entries)
       ✓ Tech stack (from app-blueprint.md §4)
       ✓ Patterns used (Loop)

       Governance assessment started (Governance Guardian)... converting app-blueprint.md → PDF...
       Evaluating architecture compliance...
       Checking pattern adherence...
       Assessment complete!

       SCORECARD: 77/100 (Grade C)
       🔴 SHOWSTOPPER: F-001 — §6 does not state the loop termination bound (the LoopAgent could run unbounded)
       🟠 HIGH: F-002 — Firestore memo store retention/versioning not documented in §6 (SR 11-7 audit)
       🟡 MEDIUM: F-003 — quality-rubric skill not pinned in §4

       Fix the showstopper and run /accelerator.assess again.

You: (document the dual exit — score>=0.90 OR 4 passes — and stall guard in §6/ADR-002; add Firestore version retention to §6)
You: /accelerator.assess

Agent: Re-extracting artifacts... assessment started...
       Assessment complete!

       SCORECARD: 90/100 (Grade A-)
       ✓ No showstoppers.
       🟡 MEDIUM: F-003 — skill pin (tech debt at generate)

       No showstoppers remain. Proceed to /accelerator.generate.
