# Build Report — PDF Translation for Eraser Assessment

The Eraser MCP server expects a PDF (not md) and returns findings as a PDF. This implements
the full round-trip. **63 tests passing (5 new PDF tests), clean lint.**

## What's built (services/governance-guardian/src/pdf/)
- `blueprint_to_pdf.py` — app-blueprint.md → PDF. Each §N section becomes a PDF section;
  every PNG referenced via `![...]()` inside a section is embedded under that same section.
  Uses the §1–§9 template structure. Markdown tables render as PDF tables. (reportlab platypus)
- `findings_to_md.py` — Eraser findings/scorecard PDF → Markdown, findings grouped into
  **Critical / High / Medium / Low** + scorecard, for the IDE. (pdfplumber; tolerates findings
  tables or labelled prose)

## Wired into the assess flow (assessment/eraser_assess.py + server/app.py)
`assess_start`:  md → PDF → **Eraser MCP server** (PLACEHOLDER seam) → findings PDF
`assess_result`: findings PDF → Markdown (Critical/High/Medium/Low) → returned to IDE as `findings_md`

Per instruction, the Eraser per-assessment call is the PLACEHOLDER seam (`eraser_mcp.assess_pdf`).
The PDF conversion in and out is real and tested. Without the Eraser client, assess_start fails
cleanly with `eraser_mcp_not_wired` (no fabrication). With a stub returning a findings PDF, the
full round-trip produces findings_md + scorecard.

## Validations (tested)
- ✅ md parsed into 9 sections; §2 and §7 PNGs associated with their sections
- ✅ Rendered PDF contains all 9 §-headers AND embeds both PNGs (verified via pdfplumber)
- ✅ Findings PDF → MD groups into Critical/High/Medium/Low with scorecard + per-section scores
- ✅ Full assess round-trip via stub Eraser: critical finding → showstopper → signal "stop"

## Doc updates (this translation was NOT previously described)
The architecture doc described solution_package as a JSON transport payload — it did not
describe the PDF round-trip. Added to:
- **architecture.md** — assess narrative now describes md→PDF (sections + embedded PNGs) →
  Eraser → findings PDF → MD (Critical/High/Medium/Low); assess_start/status/result/recordTechDebt
  tool rows added to the tool table.
- **developer-guide.md** — a "How assessment uses PDF" note in the assess section.
- **operations-runbook.md** — a troubleshooting row for the PDF conversion stages.

## Seam
The Eraser MCP client (`assess_pdf`) — the live connection to the EA office's assessment engine.
