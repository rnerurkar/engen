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
       Assessment complete!

       SCORECARD: 78/100 (Grade C)
       🔴 SHOWSTOPPER: F-001 — §6 does not state EU data residency for prospect PII (GDPR)
       🟠 HIGH: F-002 — Parallel fan-out has no documented fan-in failure policy in §6
       🟡 MEDIUM: F-003 — icp-scoring skill not pinned in §4

       Fix the showstopper and run /accelerator.assess again.

You: (add EU+US residency + AlloyDB multi-region to §6; document non-blocking fan-in policy in §6/ADR-003)
You: /accelerator.assess

Agent: Re-extracting artifacts... assessment started...
       Assessment complete!

       SCORECARD: 91/100 (Grade A-)
       ✓ No showstoppers.
       🟡 MEDIUM: F-003 — skill pin (tech debt at generate)

       No showstoppers remain. Proceed to /accelerator.generate.
