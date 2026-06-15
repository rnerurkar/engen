# Documentation

Everything Claude Code needs as context, now bundled in this folder.

## Core docs (greenfield)
- `architecture.md` — full platform architecture
- `developer-guide.md` — end-to-end developer walkthrough (includes FNOL spec/plan + system prompt)
- `operations-runbook.md` — operations

## Brownfield (CSA-TSA)
- `csa-tsa-architecture.md`, `csa-tsa-developer-guide.md`, `csa-tsa-operating-playbook.md`

## Diagrams (at this folder's root; referenced by bare filename in the docs)
Greenfield: SDLC-Accelerators-Architecture-Greenfield, -Diagram-Detailed, -GA-Architecture-Infographic,
-How-It-Works, solution-accelerator-components, solution-accelerator-sequence.mmd, refresh-sync-flow.
Brownfield: sdlc-accelerators-brownfield-architecture(+_detailed), reference-case-csa, reference-case-tsa.

## Reference (reports, IP, patent)
In `reference/`: Definition-of-Done, ARB rebranding audit, rebranding impact analysis,
provisional patent (md+docx), AgentForge-vs-SDLC IP analysis + separation, FNOL Eraser DSL examples.

## Build status
See `BUILD-REPORT-Phase1-4.md`. Reasoning-stage prompt is authored (services/solution-accelerator/prompts/);
remaining work is in `reference/SDLC-Accelerators-Definition-of-Done.md`.
