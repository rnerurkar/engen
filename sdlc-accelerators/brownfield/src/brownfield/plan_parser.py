"""Parse a brownfield plan.md into per-integration R-factor + cutover + context decisions.

Deterministic. Each '### Integration: INT-XXX' block yields a PlanDecision. R-factor vocabulary
is FIXED (rehost/replatform/refactor/rearchitect/retire) — anything else raises.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

VALID_R_FACTORS = {"rehost", "replatform", "refactor", "rearchitect", "retire"}

INT_RE = re.compile(r"^###\s+Integration:\s+(INT-\d+)\s+—\s+(.*)$", re.MULTILINE)
FIELD_RE = re.compile(r"^-\s+\*\*(.+?):\*\*\s+(.*)$", re.MULTILINE)


class InvalidRFactorError(ValueError):
    pass


@dataclass
class PlanDecision:
    integration_id: str
    r_factor: str
    cutover_strategy: str = ""
    coexistence_window: str = ""
    phase: int = 2
    rollback_path: str = ""
    coupling: str = ""
    context: dict[str, Any] = field(default_factory=dict)


def _parse_context(raw: str) -> dict[str, Any]:
    """'criticality=high, data_size_class=small' -> {criticality: high, ...}."""
    ctx = {}
    for part in raw.split(","):
        if "=" in part:
            k, _, v = part.strip().partition("=")
            ctx[k.strip()] = v.strip()
    return ctx


def parse_plan(md: str) -> list[PlanDecision]:
    """Parse a brownfield plan.md into PlanDecisions. Raises InvalidRFactorError on a bad R-factor."""
    decisions = []
    matches = list(INT_RE.finditer(md))
    for i, m in enumerate(matches):
        int_id = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        block = md[start:end]
        fields = {
            fm.group(1).strip().lower(): fm.group(2).strip()
            for fm in FIELD_RE.finditer(block)
        }
        r_factor = fields.get("r-factor", "").lower()
        if r_factor not in VALID_R_FACTORS:
            raise InvalidRFactorError(
                f"{int_id}: r-factor '{r_factor}' not in {sorted(VALID_R_FACTORS)}"
            )
        phase_raw = fields.get("phase", "2")
        _pm = re.search(r"\d+", phase_raw)
        phase = int(_pm.group()) if _pm else 2
        decisions.append(
            PlanDecision(
                integration_id=int_id,
                r_factor=r_factor,
                cutover_strategy=fields.get("cutover strategy", ""),
                coexistence_window=fields.get("coexistence window", ""),
                phase=phase,
                rollback_path=fields.get("rollback path", ""),
                coupling=fields.get("coupling", ""),
                context=_parse_context(fields.get("context dimensions", "")),
            )
        )
    return decisions
