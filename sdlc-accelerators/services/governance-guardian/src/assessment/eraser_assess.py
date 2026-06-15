"""Assess the blueprint via the Eraser MCP server using the PDF round-trip.

CONTRACT (per the PDF translation): the Eraser MCP server expects a PDF (not md) and
returns findings + scorecard as a PDF. This module:
  1. converts app-blueprint.md -> PDF (each §section a PDF section; referenced PNGs embedded)
  2. sends the PDF to the Eraser MCP server (PLACEHOLDER seam — its tools do the assessment)
  3. converts the returned findings PDF -> Markdown (Critical/High/Medium/Low) for the IDE

PER INSTRUCTION: the per-section assessment via Eraser is a PLACEHOLDER. The harness (PDF
conversion in + findings conversion out) is real and tested; the Eraser MCP call is the seam.
"""
from __future__ import annotations

import os
import tempfile

from pdf.blueprint_to_pdf import render_blueprint_pdf
from pdf.findings_to_md import convert_findings_pdf_to_md, parse_findings_pdf


def assess_blueprint_via_eraser(blueprint_md: str, assets_dir: str = ".", eraser_mcp=None) -> dict:
    """Full PDF round-trip assessment.

    eraser_mcp is the injected Eraser MCP client (its tools assess the PDF and return a
    findings PDF path). Without it, raises rather than fabricating an assessment.
    Returns {"findings_md": <markdown>, "scorecard": {...}, "findings": [...]}.
    """
    if eraser_mcp is None:
        raise NotImplementedError(
            "Blueprint assessment requires the Eraser MCP server. Wire the Eraser MCP client: "
            "it receives the blueprint PDF and returns a findings PDF. PDF conversion in/out is ready."
        )

    workdir = tempfile.mkdtemp(prefix="eraser-assess-")
    blueprint_pdf = os.path.join(workdir, "app-blueprint.pdf")

    # 1. md -> PDF (sections + embedded PNGs)
    render_blueprint_pdf(blueprint_md, blueprint_pdf, assets_dir=assets_dir)

    # 2. send PDF to Eraser MCP server -> findings PDF (PLACEHOLDER tool call)
    findings_pdf = eraser_mcp.assess_pdf(blueprint_pdf)  # returns path to findings PDF

    # 3. findings PDF -> MD (Critical/High/Medium/Low) for the IDE
    findings_md = convert_findings_pdf_to_md(findings_pdf)
    parsed = parse_findings_pdf(findings_pdf)
    return {
        "findings_md": findings_md,
        "scorecard": {"overall": parsed.overall_score, "per_section": parsed.per_section},
        "findings": [{"severity": f.severity, "section": f.section, "message": f.message}
                     for f in parsed.findings],
    }
