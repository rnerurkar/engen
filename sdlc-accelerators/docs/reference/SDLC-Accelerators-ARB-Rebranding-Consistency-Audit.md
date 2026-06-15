# Architecture Review Board — Rebranding Consistency Audit

## SDLC Accelerators (formerly AgentCatalyst) — 3-Document Suite

| Field | Value |
|---|---|
| Review Date | June 2026 |
| Reviewed By | Chief Architect, Enterprise AI (ARB) |
| Scope | Branding consistency, completeness, accuracy, referential integrity across Architecture Doc, Developer Guide, Operations Runbook |
| Rebrand | AgentCatalyst → SDLC Accelerators · Blueprint Advisor → Solution Accelerator · /catalyst.* → /accelerator.* |
| Total Findings | 12 (3 Critical, 5 High, 4 Medium) |
| Verdict | **PASS (REMEDIATED)** — all 12 findings fixed; display, identifier, referential, and asset layers fully aligned |

---

## Executive Summary

The display-name rebrand was executed correctly: "AgentCatalyst" (TitleCase), "Blueprint Advisor", and "/catalyst." commands are fully replaced across all three documents (0 residual). Protected terms (Governance Guardian, app-blueprint.*, blueprint_start/status/result) were correctly preserved.

However, the rebrand **stopped at the display layer**. Three deeper layers were missed: (1) lowercase machine identifiers (preset names, OAuth scopes, template IDs), (2) cross-document filename references (every doc still points to the OLD filenames), and (3) a critical image-path corruption where the replacement introduced SPACES into PNG filenames, breaking 3 diagram embeds. This audit catalogs all three layers.


---

## REMEDIATION STATUS — ALL 12 FINDINGS RESOLVED

| # | Severity | Finding | Status |
|---|---|---|---|
| C-1 | CRITICAL | Image paths with spaces | ✅ Fixed — hyphens restored, hero diagram repointed to greenfield PNG |
| C-2 | CRITICAL | Stale blueprint-advisor-components.png | ✅ Fixed — now solution-accelerator-components.png |
| C-3 | CRITICAL | Missing SLT-Deck diagram | ✅ Fixed — repointed to existing SDLC-Accelerators-Architecture-Greenfield.png |
| H-1 | HIGH | Cross-doc filenames | ✅ Fixed — all 3 docs reference new sdlc-accelerators-* names |
| H-2 | HIGH | Preset names | ✅ Fixed — sdlc-accelerators-enterprise/-microservice/-pipeline/-api |
| H-3 | HIGH | Template IDs | ✅ Fixed — sdlc-accelerators-spec/-plan/-tasks |
| H-4 | HIGH | Command files | ✅ Fixed — accelerator.blueprint/assess/generate/refresh.md + command: keys |
| H-5 | HIGH | MCP endpoint + version tag | ✅ Fixed — solution-accelerator.[domain].run.app, solution-accelerator/v2.3.1 |
| M-1 | MEDIUM | OAuth scope | ✅ Fixed — sdlc-accelerators.mcp |
| M-2 | MEDIUM | Preset manifest name | ✅ Fixed — name: sdlc-accelerators |
| M-3 | MEDIUM | Short-form filename | ✅ Fixed — standardized to full filename |
| M-4 | MEDIUM | Diagram title verification | ✅ Verified — solution-accelerator-components.png titled "Solution Accelerator" |

**Additional infrastructure identifiers aligned** (beyond original 12 findings, per "align all infrastructure" directive):
- Vertex AI Search data stores: sdlc-accelerators-patterns/-skills/-tools
- GitHub repos: sdlc-accelerators-skills, sdlc-accelerators-infra
- JIRA queues: SDLC-ACCELERATORS-TOOLS/-PATTERNS/-SEARCH/-SUBSTITUTIONS/-ADR/-IAC/-ADVISOR/-PRESET
- Slack channel: #sdlc-accelerators
- Entra ID group: sdlc-accelerators-users
- Env var: SDLC_ACCELERATORS_BLUEPRINT_API
- CLI command: accelerator migrate
- Cloud Run services: solution-accelerator-api, solution-accelerator-pipeline, solution-accelerator-release
- CSA-TSA docs (3): all command files, JIRA project, anchor links aligned

**Verification:** All 6 documents (3 core + 3 CSA-TSA) confirmed zero residual old-brand identifiers. All protected terms preserved (Governance Guardian, app-blueprint.*, blueprint_start/status/result, assemble_blueprint). All 5 referenced diagrams exist and resolve.

---

## CRITICAL Findings (3)

### C-1: Broken Image Paths — Rebrand Introduced Spaces into Filenames

**Severity:** CRITICAL
**Location:** Architecture doc, lines 28, 30, 253
**Finding:** The text replacement "AgentCatalyst" → "SDLC Accelerators" was applied blindly to image paths that contained "AgentCatalyst" as part of the filename. Since "SDLC Accelerators" contains a SPACE, the resulting markdown image paths are now broken:

```
Line 28:  ![...](SDLC Accelerators-Architecture-Diagram-SLT-Deck.png)
Line 30:  ![...](SDLC Accelerators-Architecture-Diagram-Detailed.png)
Line 253: ![...](SDLC Accelerators-GA-Architecture-Infographic.png)
```

The actual files use HYPHENS: `SDLC-Accelerators-Architecture-Diagram-Detailed.png`. A markdown path with an unescaped space does not resolve — **all three diagrams will fail to render.**
**Impact:** Three architecture diagrams broken. The document's primary visual content is unviewable.
**Remediation:** Replace spaces with hyphens in all three image paths:
- `SDLC Accelerators-Architecture-Diagram-SLT-Deck.png` → `SDLC-Accelerators-Architecture-Diagram-SLT-Deck.png`
- `SDLC Accelerators-Architecture-Diagram-Detailed.png` → `SDLC-Accelerators-Architecture-Diagram-Detailed.png`
- `SDLC Accelerators-GA-Architecture-Infographic.png` → `SDLC-Accelerators-GA-Architecture-Infographic.png`

### C-2: Stale Diagram Reference — blueprint-advisor-components.png

**Severity:** CRITICAL
**Location:** Architecture doc, line 314
**Finding:** The architecture doc embeds `![Solution Accelerator — Async Internal Architecture (MCP Tasks)](blueprint-advisor-components.png)`. The diagram file was renamed to `solution-accelerator-components.png` during the rebrand, but the reference in the doc was NOT updated. The old `blueprint-advisor-components.png` still exists (May 31 version, pre-rebrand), so the doc renders the OLD diagram with "Blueprint Advisor" labels.
**Impact:** The architecture doc displays a diagram with the OLD branding, directly contradicting the rebranded text around it.
**Remediation:** Update line 314 to reference `solution-accelerator-components.png`.

### C-3: SLT-Deck Diagram Referenced But Does Not Exist

**Severity:** CRITICAL
**Location:** Architecture doc, line 28
**Finding:** Line 28 references `SDLC Accelerators-Architecture-Diagram-SLT-Deck.png` (the hero diagram at the top of the document). Beyond the space-in-filename issue (C-1), this file does NOT exist in the output set at all — neither with spaces nor hyphens. The SLT-Deck diagram was an uploaded source that was never regenerated with SDLC Accelerators branding.
**Impact:** The document's hero/title diagram is missing entirely. Even after fixing the space issue, the path resolves to a non-existent file.
**Remediation:** Regenerate the SLT-Deck architecture diagram with SDLC Accelerators branding (this was the diagram updated in a prior turn — `SDLC-Accelerators-Architecture-Greenfield.png` may be the intended replacement). Either regenerate `SDLC-Accelerators-Architecture-Diagram-SLT-Deck.png` or update the reference to point to the existing greenfield diagram.

---

## HIGH Findings (5)

### H-1: Cross-Document Filename References All Point to OLD Filenames

**Severity:** HIGH
**Location:** All 3 docs — Architecture (lines 1321-1323, 1332), Developer Guide (lines 6, 2180, 2213-2215), Operations Runbook (lines 12-14)
**Finding:** Every cross-reference between the three documents still cites the OLD filenames:
- `agentcatalyst-architecture-archetype-agnostic.md` (should be `sdlc-accelerators-architecture-archetype-agnostic.md`)
- `agentcatalyst-archetype-agnostic-developer-guide.md` (should be `sdlc-accelerators-archetype-agnostic-developer-guide.md`)
- `agentcatalyst-operations-greenfield_runbook.md` (should be `sdlc-accelerators-operations-greenfield_runbook.md`)
- `agentcatalyst-architecture.md` (short form, dev guide lines 6, 2180)

The documents were renamed at the filesystem level, but the references INSIDE the documents that point to each other were not updated. A reader following "see the Architecture Document (`agentcatalyst-architecture.md`)" will hit a 404.
**Impact:** All inter-document navigation is broken. The "Related Documents" tables in all three docs are inaccurate.
**Remediation:** Update all filename references to the new `sdlc-accelerators-*` names. Note the dev guide uses a short form `agentcatalyst-architecture.md` that doesn't match the actual longer filename — standardize to the full name.

### H-2: Preset Names Not Rebranded (agentcatalyst-enterprise, -microservice, -pipeline, -api)

**Severity:** HIGH
**Location:** Architecture doc lines 95-98, 112, 243, 672, 1332; Developer Guide (similar)
**Finding:** The preset identifiers remain on the old brand:
- `agentcatalyst-enterprise` (the main preset developers install)
- `agentcatalyst-microservice`, `agentcatalyst-pipeline`, `agentcatalyst-api` (archetype variants)

These appear in install commands developers will actually type: `specify preset add agentcatalyst-enterprise`. This is the literal command-line identifier — if the platform team renames the preset to match the new brand, these docs are wrong; if they keep the old preset name, there's a brand mismatch between the product (SDLC Accelerators) and the preset (agentcatalyst-enterprise).
**Impact:** Developer-facing install commands reference old brand. Decision needed: rename presets or document the discrepancy.
**Remediation:** Decide preset naming. Recommended: rename to `sdlc-accelerators-enterprise`, `sdlc-accelerators-microservice`, etc. Update all install commands and the archetype table.

### H-3: Template IDs Not Rebranded (agentcatalyst-spec, -plan, -tasks)

**Severity:** HIGH
**Location:** Architecture doc lines 1369, 1428, 1480, 1524
**Finding:** The preset's template identifiers in the YAML appendix remain old-brand:
```
name: agentcatalyst
template: agentcatalyst-spec
template: agentcatalyst-plan
template: agentcatalyst-tasks
```
These are machine identifiers consumed by the spec-kit tooling.
**Impact:** If presets are rebranded (H-2), these template IDs must match. If not, internal inconsistency between preset name and template IDs.
**Remediation:** Align template IDs with the preset naming decision from H-2.

### H-4: Command File Names Not Rebranded (catalyst.blueprint.md, catalyst.assess.md, catalyst.generate.md)

**Severity:** HIGH
**Location:** Architecture doc lines 1342-1344, 1568, 1614, 1669
**Finding:** The command definition FILES in the preset directory structure retain the old prefix:
```
catalyst.blueprint.md   ← P1: Solution Accelerator call
catalyst.assess.md      ← P2: Governance Guardian call
catalyst.generate.md    ← P3
command: catalyst.blueprint
command: catalyst.assess
command: catalyst.generate
```
Note: the COMMANDS themselves were rebranded to `/accelerator.*` in the prose, but the FILES that define them and the `command:` YAML keys still say `catalyst.*`. This is an internal contradiction — the doc says developers type `/accelerator.blueprint` but the command is defined in `catalyst.blueprint.md` with `command: catalyst.blueprint`.
**Impact:** The command definitions don't match the documented commands. If implemented as written, `/accelerator.blueprint` would not resolve because the command file defines `catalyst.blueprint`.
**Remediation:** Rename command files to `accelerator.blueprint.md`, `accelerator.assess.md`, `accelerator.generate.md` and update the `command:` keys to match.

### H-5: Operations Runbook MCP Endpoint and Version Tag Not Rebranded

**Severity:** HIGH
**Location:** Operations Runbook lines 242, 553
**Finding:** Two operational identifiers remain old-brand:
- Line 242: `--mcp-endpoint mcp://blueprint-advisor.[company-domain].run.app` (the actual MCP Server hostname)
- Line 553: `# Generated by: blueprint-advisor/v2.3.1` (version tag in generated artifacts)

The MCP endpoint hostname is operationally significant — it's the actual Cloud Run service URL the ops team monitors and the coding agent connects to.
**Impact:** Ops team monitors a hostname that contradicts the product brand. If the Cloud Run service is renamed to match, this runbook command is wrong.
**Remediation:** Decide whether the Cloud Run service is renamed. If yes, update to `solution-accelerator.[company-domain].run.app`. Update the version-tag generator to `solution-accelerator/v2.3.1`.

---

## MEDIUM Findings (4)

### M-1: OAuth Scope Identifier Not Rebranded (agentcatalyst.mcp)

**Severity:** MEDIUM
**Location:** Architecture doc lines 608, 621, 663
**Finding:** The OAuth 2.1 audience scope is `agentcatalyst.mcp`:
```
scope=agentcatalyst.mcp
Verify audience = agentcatalyst.mcp
Single audience scope (agentcatalyst.mcp)
```
This is an Entra ID app registration identifier. Changing it requires coordinating with the identity team and re-registering the app.
**Impact:** OAuth scope contradicts brand, but changing it is an identity-infrastructure operation, not just a doc edit.
**Remediation:** Decide with identity team whether to re-register the scope as `sdlc-accelerators.mcp` or `solution-accelerator.mcp`. If kept for stability, add a note explaining the scope name predates the rebrand.

### M-2: Preset 'name:' Field in YAML (name: agentcatalyst)

**Severity:** MEDIUM
**Location:** Architecture doc line 1369
**Finding:** The preset manifest's `name: agentcatalyst` field is the canonical preset identifier. Related to H-2/H-3 but specifically the manifest name field.
**Impact:** Canonical preset name unchanged.
**Remediation:** Align with H-2 preset naming decision.

### M-3: Developer Guide Short-Form Filename Inconsistent

**Severity:** MEDIUM
**Location:** Developer Guide lines 6, 2180
**Finding:** The dev guide references `agentcatalyst-architecture.md` (short form) while the Related Documents table uses `agentcatalyst-architecture-archetype-agnostic.md` (full form). Even pre-rebrand, these two references were inconsistent with each other. The rebrand should standardize both to the actual filename.
**Impact:** Two different filenames cited for the same document.
**Remediation:** Standardize all references to the actual filename `sdlc-accelerators-architecture-archetype-agnostic.md`.

### M-4: Diagram Alt-Text vs Filename Mismatch Risk

**Severity:** MEDIUM
**Location:** Architecture doc line 314
**Finding:** After C-2 is fixed, verify the alt-text "Solution Accelerator — Async Internal Architecture (MCP Tasks)" matches the regenerated diagram's actual title. The diagram was regenerated; confirm its embedded title also says "Solution Accelerator" not "Blueprint Advisor."
**Impact:** Alt-text and diagram content could disagree.
**Remediation:** Confirm `solution-accelerator-components.png` internal title reads "Solution Accelerator."

---

## What Was Done Correctly

| Item | Status |
|---|---|
| "AgentCatalyst" (TitleCase) display name | ✅ 0 residual in all 3 docs |
| "Blueprint Advisor" display name | ✅ 0 residual in all 3 docs |
| "/catalyst." commands in prose | ✅ 0 residual, all → /accelerator. |
| Governance Guardian (protected) | ✅ Preserved (30+11+11 refs intact) |
| app-blueprint.md/.json (protected) | ✅ Preserved (79+34+10 refs intact) |
| blueprint_start/status/result (protected) | ✅ Preserved (MCP API names intact) |
| assemble_blueprint, validate_composition (protected) | ✅ Preserved |
| Inline mermaid diagram labels | ✅ Rebranded (Solution Accelerator, /accelerator.*) |

---

## Findings Summary

| Severity | Count | Theme |
|---|---|---|
| **CRITICAL** | 3 | Broken/missing diagram references (space-in-path, stale filename, non-existent file) |
| **HIGH** | 5 | Machine identifiers not rebranded (cross-doc filenames, preset names, template IDs, command files, MCP endpoint) |
| **MEDIUM** | 4 | Infrastructure identifiers requiring cross-team coordination (OAuth scope, preset manifest, short-form filename) |

## Root Cause

The rebrand applied **display-name replacements** (TitleCase "AgentCatalyst", "Blueprint Advisor") but did not extend to **three identifier layers**: (1) lowercase machine identifiers (`agentcatalyst-enterprise`, `catalyst.blueprint`, `agentcatalyst.mcp`), (2) cross-document filename references, and (3) image embed paths (where "SDLC Accelerators" with its space corrupted PNG paths). A complete rebrand must address display names, machine identifiers, file references, and asset paths as four distinct layers.

## Recommended Action

Fix all 3 Critical findings immediately (diagrams are broken). Resolve the H-2/H-3/H-4/H-5 identifier decisions with the platform and identity teams (rename vs document-discrepancy), then apply consistently. Medium findings require cross-team coordination and can follow.

---

*Architecture Review Board — Confidential — Not for External Distribution*
