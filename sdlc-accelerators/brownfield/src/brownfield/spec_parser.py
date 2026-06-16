"""Parse a brownfield spec.md into structured integration blocks (8-signal fields).

Deterministic markdown parsing. Each '### Integration: INT-XXX' block becomes an Integration
with the eight migration-readiness signal fields. The csa-extractor (diagram parsing) pre-fills
these blocks upstream; this parser reads the resulting spec.md.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

INT_RE = re.compile(r"^###\s+Integration:\s+(INT-\d+)\s+—\s+(.*)$", re.MULTILINE)
FIELD_RE = re.compile(r"^-\s+\*\*(.+?):\*\*\s+(.*?)(?:\s+\[Signal:.*\])?$", re.MULTILINE)


@dataclass
class Integration:
    integration_id: str
    name: str
    fields: dict = field(default_factory=dict)

    def get(self, key: str, default: str = "") -> str:
        """Case-insensitive lookup of a signal field on this integration."""
        return self.fields.get(key.lower(), default)


@dataclass
class BrownfieldSpec:
    summary: str = ""
    scope: str = ""
    integrations: list = field(default_factory=list)
    nfrs: dict = field(default_factory=dict)


def parse_spec(md: str) -> BrownfieldSpec:
    """Parse a brownfield spec.md into a BrownfieldSpec with one Integration per §-block."""
    spec = BrownfieldSpec()
    matches = list(INT_RE.finditer(md))
    for i, m in enumerate(matches):
        int_id, name = m.group(1), m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        block = md[start:end]
        fields = {}
        for fm in FIELD_RE.finditer(block):
            fields[fm.group(1).strip().lower()] = fm.group(2).strip()
        spec.integrations.append(Integration(integration_id=int_id, name=name, fields=fields))
    return spec
