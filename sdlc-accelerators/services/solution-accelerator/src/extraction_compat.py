"""Shim: section extraction (mirrors governance-guardian extraction/sections.py)."""

from __future__ import annotations

import re


def extract_sections_compat(blueprint_md: str) -> dict[int, str]:
    sections: dict[int, str] = {}
    pattern = re.compile(r"^##\s*§\s*(\d+)\.?\s", re.MULTILINE)
    matches = list(pattern.finditer(blueprint_md))
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(blueprint_md)
        sections[num] = blueprint_md[start:end].strip()
    return sections
