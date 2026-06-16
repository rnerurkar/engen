"""PDF round-trip for Eraser assessment: md->PDF (sections + embedded PNGs) and findings PDF->MD."""
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from pdf.blueprint_to_pdf import parse_blueprint_md, render_blueprint_pdf
from pdf.findings_to_md import convert_findings_pdf_to_md, parse_findings_pdf

BP_MD = """# Blueprint
## §1. Application Overview
Overview text.
## §2. Component Topology Diagram
![Component](diagrams/component.png)
## §3. Architecture Patterns
| Pattern | Role |
|---|---|
| SequentialAgent | orchestration |
## §4. Application Tech Stack
ADK.
## §5. DevSecOps Stack
Model Armor.
## §6. HA/DR Guidance
Warm Standby.
## §7. HA/DR Lifecycle Diagrams
![HADR](diagrams/hadr.png)
## §8. Architecture Decision Log
Decisions.
## §9. Non-Functional Requirements
| NFR | Target |
|---|---|
| availability | 99.9% |
"""


def _make_pngs(d):
    os.makedirs(os.path.join(d, "diagrams"), exist_ok=True)
    try:
        from PIL import Image
        for n in ["component", "hadr"]:
            Image.new("RGB", (400, 200), "#ffffff").save(os.path.join(d, "diagrams", f"{n}.png"))
        return True
    except ImportError:
        return False


def test_parse_blueprint_sections_and_images():
    secs = parse_blueprint_md(BP_MD)
    assert len(secs) == 9
    s2 = next(s for s in secs if s.number == 2)
    assert s2.images == ["diagrams/component.png"]
    s7 = next(s for s in secs if s.number == 7)
    assert s7.images == ["diagrams/hadr.png"]


def test_render_blueprint_pdf_has_sections_and_embeds_pngs():
    import pdfplumber
    d = tempfile.mkdtemp()
    has_png = _make_pngs(d)
    out = render_blueprint_pdf(BP_MD, os.path.join(d, "bp.pdf"), assets_dir=d)
    assert os.path.exists(out)
    with pdfplumber.open(out) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        n_images = sum(len(p.images) for p in pdf.pages)
    for i in range(1, 10):
        assert f"§{i}." in text
    if has_png:
        assert n_images == 2  # both PNGs embedded under their sections


def _make_findings_pdf(d):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table
    path = os.path.join(d, "findings.pdf")
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=letter)
    doc.build([
        Paragraph("Overall: 78/100", styles["Heading2"]),
        Paragraph("§2: 0.9, §6: 0.6", styles["Normal"]),
        Table([["Severity", "Section", "Finding"],
               ["Critical", "§6", "No cross-region DR"],
               ["High", "§5", "WAF not managed group"],
               ["Medium", "§4", "Angular 17 off radar"],
               ["Low", "§9", "Tighten latency"]]),
    ])
    return path


def test_findings_pdf_to_md_categories():
    d = tempfile.mkdtemp()
    pdf = _make_findings_pdf(d)
    parsed = parse_findings_pdf(pdf)
    assert parsed.overall_score == "78"
    assert len(parsed.findings) == 4
    md = convert_findings_pdf_to_md(pdf)
    assert "## 🔴 Critical (1)" in md
    assert "## 🟠 High (1)" in md
    assert "## 🟡 Medium (1)" in md
    assert "## ⚪ Low (1)" in md
    assert "No cross-region DR" in md


def test_findings_md_includes_scorecard():
    d = tempfile.mkdtemp()
    md = convert_findings_pdf_to_md(_make_findings_pdf(d))
    assert "Overall score:** 78" in md
    assert "1 critical, 1 high, 1 medium, 1 low" in md
