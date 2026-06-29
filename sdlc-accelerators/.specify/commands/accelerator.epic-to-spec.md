# /accelerator.epic-to-spec (Brownfield) — Rally Epic + CSA → canonical spec.md

The **front door** for the brownfield archetype. It fuses a Rally Epic's modernization intent with the
upstream CSA (Current-State Architecture) and emits the **final** `spec.md` directly — so you do **not**
run `/speckit.specify`. From the produced `spec.md`, `/speckit.plan` (and everything after) follows
**unchanged**.

## Preconditions (Step 0 is OUTSIDE this preset)
1. **CSA Agent (upstream, separate system).** A CSA Agent in the IDE reverse-engineers the legacy
   application into a **CSA diagram** and an accompanying **`architecture.md`**, both keyed by stable IDs
   (`CSA-COMP-XXX` components, `INT-XXX` integrations). Both files live in the workspace. SDLC
   Accelerators Brownfield begins only after they exist. → *Architecture §7 (CSA Agent handoff).*
2. **BA / Solution Architect authors the Epic.** Using the standard Rally Epic template, the analyst
   fills a **Modernization Scope** table declaring, per CSA component, a **disposition** (`Refactor` |
   `Rehost`) and an **AWS target**:

   ```
   ## Modernization Scope
   | Component    | Disposition | AWS Target                       | Rationale            |
   |--------------|-------------|----------------------------------|----------------------|
   | CSA-COMP-001 | Refactor    | ECS Fargate + Aurora PostgreSQL  | break the monolith   |
   | CSA-COMP-002 | Rehost      | EC2 (lift-and-shift)             | vendor-locked adapter|
   ```

## Steps (coding agent)
1. Ask the developer for the Rally Epic **FormattedID** (capability-negotiated interview).
2. Fetch the Epic via the **Rally MCP server** (`.vscode/mcp.json`, Entra ID SSO — credentials stay in
   the IDE). Use the registered read tools (discover from the server). Capture `ObjectVersion` +
   `LastUpdateDate`.
3. Read the CSA **`architecture.md`** from the workspace (the file the CSA Agent produced).
4. Call the brownfield MCP tool `epic_to_spec_start` with
   `{ epic: <epic-content>, csa_architecture_md: <architecture.md content> }` (content only — no
   credentials). The server runs the three-phase pipeline:
   - **Phase A — Resolve & validate:** parse the Epic's Modernization Scope table, load the CSA
     registry, and **cross-walk** every Epic-named component against the CSA. Components the CSA lacks
     are surfaced (you cannot modernize what the current state does not contain); CSA components the
     Epic omits are stamped out-of-scope.
   - **Phase B — Compose:** render the canonical `spec.md` — per-component modernization units
     (`Refactor`/`Rehost` + AWS target + disposition-specific migration considerations) plus the
     **CSA-sourced 8-signal Integration Inventory** that `/speckit.plan` and the readiness gate consume
     unchanged.
   - **Phase C — Gate & trace:** score the spec with the SAME `validate_spec` gate; emit the
     `modernization-scope-ledger.json` (component → disposition → target → source spans) and stamp
     provenance for **both** sources (Epic FormattedID + ObjectVersion **and** the CSA `architecture.md`
     hash).
5. Poll `epic_to_spec_status({ taskId })` every `pollInterval` ms; report each `phase`
   (`resolving`/`composing`/`gating`).
6. On `completed`, call `epic_to_spec_result({ taskId })`. It returns `spec.md`,
   `modernization-scope-ledger.json`, `resolved_scope` (in/out/unresolved + invalid dispositions),
   `per_component_confidence`, and `blueprint_gate`.
7. Write `spec.md` + `modernization-scope-ledger.json` to the workspace. The developer resolves any
   `[NEEDS CLARIFICATION]`, **unresolved** components, and **invalid dispositions**, then runs
   `/speckit.plan` → `/accelerator.blueprint` directly. **No `/speckit.specify` step.**

## Notes
- **Replaces `/speckit.specify`** for the Epic-driven path. `/speckit.specify` (the `csa-extractor`
  override) remains available as a **no-Epic manual fallback** — same CSA extraction, without an Epic.
- **Dispositions:** `Refactor` (re-architect into AWS-native; strangler-fig decommission) and `Rehost`
  (lift-and-shift; remap network/identity; defer re-architecture as tech-debt). Other migration "R's"
  are out of scope for this preset; an unrecognized disposition is flagged, not silently accepted.
- **Determinism:** the fusion path runs **no LLM** — same Epic + same CSA → identical `spec.md`. (When no
  CSA is present yet, ingestion degrades to a legacy extractive Epic-only path and tells you to supply
  the CSA or use `/speckit.specify`.)
- **Staleness:** `/accelerator.refresh` reads the durable `modernization-scope-ledger.json` provenance
  and compares **both** Rally's current `ObjectVersion` **and** the CSA `architecture.md` hash, so drift
  in either source is detected.
- The readiness gate still requires a meaningful integration inventory; thin CSAs surface CLARIFY markers.
