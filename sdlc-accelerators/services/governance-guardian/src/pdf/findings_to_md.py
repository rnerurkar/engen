"""Convert the Eraser MCP server's findings/scorecard PDF -> Markdown for the IDE.

Eraser returns findings + a scorecard as a PDF. This extracts them (pdfplumber) and
emits a Markdown document grouped into Critical / High / Medium / Low categories, plus
the scorecard, for the coding agent to write into the workspace.

Built with pdfplumber per the PDF skill. The extraction is tolerant of two shapes:
a findings TABLE (severity | section | message), or labelled prose lines.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pdfplumber

SEVERITIES = ["critical", "high", "medium", "low"]
SEV_RE = re.compile(r"\b(critical|high|medium|low)\b", re.IGNORECASE)
SCORE_RE = re.compile(r"(?:overall|score)[:\s]+(\d+(?:\.\d+)?)\s*(?:/\s*100|%)?", re.IGNORECASE)


@dataclass
class Finding:
    severity: str
    section: str
    message: str


@dataclass
class FindingsDoc:
    overall_score: str = ""
    findings: list[Finding] = field(default_factory=list)
    per_section: dict = field(default_factory=dict)


def _extract_from_tables(pdf) -> list[Finding]:
    findings = []
    for page in pdf.pages:
        for table in page.extract_tables() or []:
            if not table or len(table) < 2:
                continue
            header = [(c or "").strip().lower() for c in table[0]]
            # locate columns
            sev_i = next((i for i, h in enumerate(header) if "sever" in h), None)
            sec_i = next((i for i, h in enumerate(header) if "section" in h), None)
            msg_i = next((i for i, h in enumerate(header) if "finding" in h or "message" in h or "detail" in h), None)
            if sev_i is None:
                continue
            for row in table[1:]:
                if not row or sev_i >= len(row) or not row[sev_i]:
                    continue
                sev = row[sev_i].strip().lower()
                if sev not in SEVERITIES:
                    m = SEV_RE.search(row[sev_i])
                    sev = m.group(1).lower() if m else "low"
                findings.append(Finding(
                    severity=sev,
                    section=(row[sec_i].strip() if sec_i is not None and sec_i < len(row) and row[sec_i] else ""),
                    message=(row[msg_i].strip() if msg_i is not None and msg_i < len(row) and row[msg_i] else ""),
                ))
    return findings


def _extract_from_text(text: str) -> list[Finding]:
    findings = []
    for line in text.splitlines():
        m = SEV_RE.search(line)
        if not m:
            continue
        sev = m.group(1).lower()
        msg = SEV_RE.sub("", line).strip(" :-\t")
        sec_m = re.search(r"§?\s*(\d+)", line)
        findings.append(Finding(severity=sev, section=(f"§{sec_m.group(1)}" if sec_m else ""), message=msg))
    return findings


def parse_findings_pdf(pdf_path: str) -> FindingsDoc:
    """Extract scorecard + findings from the Eraser findings PDF."""
    doc = FindingsDoc()
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)
        # scorecard
        sm = SCORE_RE.search(full_text)
        if sm:
            doc.overall_score = sm.group(1)
        # findings: prefer tables, fall back to text
        table_findings = _extract_from_tables(pdf)
        doc.findings = table_findings if table_findings else _extract_from_text(full_text)
        # per-section scores like "§2: 0.9"
        for m in re.finditer(r"§\s*(\d+)\s*[:=]\s*(\d+(?:\.\d+)?)", full_text):
            doc.per_section[f"§{m.group(1)}"] = m.group(2)
    return doc


def render_findings_md(doc: FindingsDoc) -> str:
    """Render the findings as Markdown grouped by Critical/High/Medium/Low."""
    out = ["# Governance Assessment — Findings\n"]
    if doc.overall_score:
        out.append(f"**Overall score:** {doc.overall_score}/100\n")
    if doc.per_section:
        out.append("**Per-section scores:** " +
                   ", ".join(f"{k} {v}" for k, v in sorted(doc.per_section.items())) + "\n")

    counts = {s: 0 for s in SEVERITIES}
    for f in doc.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    out.append("**Summary:** " +
               ", ".join(f"{counts[s]} {s}" for s in SEVERITIES) + "\n")

    labels = {"critical": "🔴 Critical", "high": "🟠 High", "medium": "🟡 Medium", "low": "⚪ Low"}
    for sev in SEVERITIES:
        items = [f for f in doc.findings if f.severity == sev]
        out.append(f"\n## {labels[sev]} ({len(items)})\n")
        if not items:
            out.append("_None._\n")
            continue
        for f in items:
            sec = f" [{f.section}]" if f.section else ""
            out.append(f"- {f.message}{sec}")
        out.append("")
    return "\n".join(out) + "\n"


def convert_findings_pdf_to_md(pdf_path: str) -> str:
    """Top-level: Eraser findings PDF -> Markdown string for the IDE."""
    return render_findings_md(parse_findings_pdf(pdf_path))
