You: /accelerator.assess

Agent: Extracting solution artifacts from workspace...
       ✓ TSA component diagram (component-topology.drawio.xml)
       ✓ HA/DR views (1 view found)
       ✓ NFRs (from app-blueprint.md §9)
       ✓ Architecture Decision Log (4 entries)
       ✓ Tech stack (from app-blueprint.md §4)
       ✓ Patterns used (single LlmAgent, dynamic tool use)

       Governance assessment started (Governance Guardian)... converting app-blueprint.md → PDF...
       Evaluating architecture compliance...
       Scoring HA/DR readiness...
       Assessment complete!

       SCORECARD: 76/100 (Grade C)
       🔴 SHOWSTOPPER: F-001 — Payment tool on the single agent with no documented PAN-masking control in §5 (PCI-DSS)
       🟠 HIGH: F-002 — No documented bound on the reasoning loop in §6 (cost/availability risk)
       🟡 MEDIUM: F-003 — Refund-policy skill version not pinned in §4

       Fix the showstopper and run /accelerator.assess again.

You: (add Model Armor PAN-masking + payments scoping note to §5; document the 8-step cap in §6/ADR-002)
You: /accelerator.assess

Agent: Re-extracting artifacts... assessment started...
       Assessment complete!

       SCORECARD: 90/100 (Grade A-)
       ✓ No showstoppers.
       🟡 MEDIUM: F-003 — skill-version pin (tech debt at generate)

       No showstoppers remain. Proceed to /accelerator.generate.
