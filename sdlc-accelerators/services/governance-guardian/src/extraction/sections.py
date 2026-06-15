"""Deterministic extraction of the 9 governance sections from app-blueprint.md.
This is platform code (fully implemented). The ASSESSMENT of these sections is
the human-authored EA rubric (see assessment/engine.py).
"""
from __future__ import annotations

import re

SECTION_TITLES = {
    1: "Application Overview",
    2: "Component Topology Diagram",
    3: "Architecture Patterns",
    4: "Application Tech Stack",
    5: "DevSecOps Stack",
    6: "HA/DR Guidance",
    7: "HA/DR Lifecycle Diagrams",
    8: "Architecture Decision Log",
    9: "Non-Functional Requirements",
}


def extract_sections(blueprint_md: str) -> dict[int, str]:
    """Split app-blueprint.md into its 9 sections by '## §N.' headers."""
    sections: dict[int, str] = {}
    # Match headers like '## §1.' or '## §1 ' etc.
    pattern = re.compile(r"^##\s*§\s*(\d+)\.?\s", re.MULTILINE)
    matches = list(pattern.finditer(blueprint_md))
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(blueprint_md)
        sections[num] = blueprint_md[start:end].strip()
    return sections


def completeness(sections: dict[int, str]) -> list[str]:
    """Return list of missing section numbers (as findings)."""
    return [f"Missing §{n} ({SECTION_TITLES[n]})" for n in range(1, 10) if n not in sections]
