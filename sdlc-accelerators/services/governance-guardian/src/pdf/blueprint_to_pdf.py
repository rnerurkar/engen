"""Convert app-blueprint.md -> PDF for the Eraser MCP server (which expects PDF, not md).

Each §N markdown section becomes a section in the PDF. Each PNG referenced via
![...](path) inside a section is embedded in the PDF under that same section.
Uses the §1-§9 template structure (same sections as the md template).

Built with reportlab platypus per the PDF skill. PNG paths resolve against an assets dir.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
SECTION_RE = re.compile(r"^##\s*§\s*(\d+)\.?\s*(.*)$", re.MULTILINE)


@dataclass
class BlueprintSection:
    number: int
    title: str
    body: str
    images: list[str] = field(default_factory=list)


def parse_blueprint_md(md: str) -> list[BlueprintSection]:
    """Split app-blueprint.md into §1-§9 sections, capturing referenced PNG paths per section."""
    matches = list(SECTION_RE.finditer(md))
    sections = []
    for i, m in enumerate(matches):
        num = int(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[start:end].strip()
        images = [img[1] for img in IMG_RE.findall(body)]
        sections.append(BlueprintSection(number=num, title=title, body=body, images=images))
    return sections


def _md_table_to_flowable(block: str, styles):
    """Convert a markdown table block to a reportlab Table; return None if not a table."""
    lines = [ln for ln in block.splitlines() if ln.strip().startswith("|")]
    if len(lines) < 2:
        return None
    rows = []
    for ln in lines:
        if re.match(r"^\s*\|[\s:|-]+\|\s*$", ln):  # separator row
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        rows.append([Paragraph(c, styles["BodyText"]) for c in cells])
    if not rows:
        return None
    t = Table(rows, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def render_blueprint_pdf(md: str, output_path: str, assets_dir: str = ".") -> str:
    """Render the app-blueprint.md to a PDF, embedding PNGs under their sections."""
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("SecHead", parent=styles["Heading1"], fontSize=14,
                        textColor=colors.HexColor("#2c3e50"), spaceBefore=12, spaceAfter=6)
    caption = ParagraphStyle("Caption", parent=styles["Italic"], fontSize=8,
                             textColor=colors.grey, spaceAfter=10)

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    story = []
    sections = parse_blueprint_md(md)

    # Title
    story.append(Paragraph("Application Blueprint — Governance Assessment Package", styles["Title"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"{len(sections)} governance sections (§1–§9)", caption))
    story.append(Spacer(1, 12))

    for sec in sections:
        story.append(Paragraph(f"§{sec.number}. {sec.title}", h1))

        # Body: split into table blocks and prose; embed images where referenced
        remaining = IMG_RE.sub("", sec.body)  # prose without the image markdown
        # render tables and prose paragraphs
        blocks = re.split(r"\n\s*\n", remaining)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            tbl = _md_table_to_flowable(block, styles)
            if tbl is not None:
                story.append(tbl)
                story.append(Spacer(1, 8))
            else:
                clean = re.sub(r"[#*`>]", "", block).strip()
                if clean:
                    story.append(Paragraph(clean, styles["BodyText"]))
                    story.append(Spacer(1, 4))

        # Embed each referenced PNG under this section
        for img_path in sec.images:
            resolved = img_path if os.path.isabs(img_path) else os.path.join(assets_dir, img_path)
            if os.path.exists(resolved):
                try:
                    img = Image(resolved)
                    max_w = 6.5 * inch
                    if img.drawWidth > max_w:
                        ratio = max_w / img.drawWidth
                        img.drawWidth = max_w
                        img.drawHeight *= ratio
                    story.append(img)
                    story.append(Paragraph(f"Figure: {os.path.basename(img_path)}", caption))
                except Exception:
                    story.append(Paragraph(f"[diagram: {os.path.basename(img_path)} — embed failed]", caption))
            else:
                story.append(Paragraph(f"[diagram: {os.path.basename(img_path)} — not found at render time]", caption))

        story.append(Spacer(1, 10))

    doc.build(story)
    return output_path
