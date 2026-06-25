You: /accelerator.assess

Agent: Extracting solution artifacts from workspace...
       ✓ TSA component diagram (component-topology.drawio.xml)
       ✓ HA/DR views (1 view found)
       ✓ NFRs (from app-blueprint.md §9)
       ✓ Architecture Decision Log (4 entries)
       ✓ Tech stack (from app-blueprint.md §4)
       ✓ Patterns used (Sequential, Parallel)

       Governance assessment started (Governance Guardian)... converting app-blueprint.md → PDF...
       Evaluating architecture compliance...
       Checking pattern adherence...
       Scoring HA/DR readiness...
       Assessment complete!

       SCORECARD: 79/100 (Grade C)
       🔴 SHOWSTOPPER: F-001 — §6 omits the branch-failure (fan-in) policy for the Parallel assessments (availability/data-integrity)
       🟠 HIGH: F-002 — SIU referral path not represented in the decision log §8
       🟡 MEDIUM: F-003 — actuarial-pricing skill not pinned in §4

       Fix the showstopper and run /accelerator.assess again.

You: (document non-blocking branch policy + pending flags in §6; add SIU-referral ADR to §8)
You: /accelerator.assess

Agent: Re-extracting artifacts... assessment started...
       Assessment complete!

       SCORECARD: 92/100 (Grade A-)
       ✓ No showstoppers.
       🟡 MEDIUM: F-003 — skill pin (tech debt at generate)

       No showstoppers remain. Proceed to /accelerator.generate.
