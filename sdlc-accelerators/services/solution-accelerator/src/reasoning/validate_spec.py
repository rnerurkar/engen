"""validate_spec — deterministic signal extraction + quality gate (NOT a reasoning step).

Reads spec.md as MARKDOWN TEXT (per architecture — spec/plan are never converted to JSON).
Scans §2 for ordering words, §5 for own-system flags, §10 for measurable criteria, and
produces a spec_quality_score (0-100) with PASS/WARN/BLOCK per section + the documented
guidance messages. This is Step 0 of blueprint_start.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

Status = Literal["PASS", "WARN", "BLOCK"]

ORDERING_WORDS = [
    "first",
    "then",
    "in parallel",
    "loop until",
    "route to human",
    "route to a human",
]
OWN_SYSTEM_FLAGS = [
    "operate their own",
    "operates their own",
    "own system",
    "their own system",
]
MEASURABLE = re.compile(
    r"(<\s*\d|>\s*\d|\d+\s*%|\d+\s*(min|sec|ms|hours?|days?))", re.IGNORECASE
)


@dataclass
class SectionFinding:
    section: str
    status: Status
    signals_found: int
    guidance: str = ""


@dataclass
class SpecSignals:
    """Deterministically extracted signals — the input the LLM reasons over."""

    ordering_words: list[str] = field(default_factory=list)
    own_system_partners: list[str] = field(default_factory=list)
    measurable_criteria: list[str] = field(default_factory=list)
    data_systems: list[str] = field(default_factory=list)


@dataclass
class SpecValidation:
    quality_score: int
    findings: list[SectionFinding]
    signals: SpecSignals

    @property
    def blocked(self) -> bool:
        return any(f.status == "BLOCK" for f in self.findings)


def _section(md: str, num: int) -> str:
    """Extract a §N section body from spec.md (markdown). Supports '## §N', '## N.', '## Section N'."""
    patterns = [
        rf"^#{{1,3}}\s*§\s*{num}\b",
        rf"^#{{1,3}}\s*{num}\.",
        rf"^#{{1,3}}\s*Section\s+{num}\b",
    ]
    lines = md.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if any(re.match(p, ln, re.IGNORECASE) for p in patterns):
            start = i
            break
    if start is None:
        return ""
    # until next header of same level
    for j in range(start + 1, len(lines)):
        if re.match(r"^#{1,3}\s", lines[j]):
            return "\n".join(lines[start:j])
    return "\n".join(lines[start:])


def extract_signals(spec_md: str) -> SpecSignals:
    """Deterministic signal extraction from spec.md markdown."""
    s2 = _section(spec_md, 2).lower()
    s4 = _section(spec_md, 4)
    s10 = _section(spec_md, 10)

    ordering = [w for w in ORDERING_WORDS if w in s2]
    own = []
    for line in _section(spec_md, 5).splitlines():
        if any(flag in line.lower() for flag in OWN_SYSTEM_FLAGS):
            own.append(line.strip("-* ").strip())
    measurable = MEASURABLE.findall(s10)
    measurable = [m[0] if isinstance(m, tuple) else m for m in measurable]
    # data systems: bulleted / comma items in §4 (proper-noun-ish tokens)
    data_systems = []
    for line in s4.splitlines():
        line = line.strip("-*• ").strip()
        if line and not re.match(r"^#{1,3}", line) and len(line) < 80:
            data_systems.append(line)

    return SpecSignals(
        ordering_words=ordering,
        own_system_partners=own,
        measurable_criteria=[str(m) for m in measurable],
        data_systems=[d for d in data_systems if d][:20],
    )


def validate_spec(spec_md: str) -> SpecValidation:
    """Quality gate: score signals, emit PASS/WARN/BLOCK with guidance."""
    sig = extract_signals(spec_md)
    findings: list[SectionFinding] = []

    # §2 ordering words: ≥3 PASS, 1-2 WARN, 0 BLOCK
    n = len(sig.ordering_words)
    if n >= 3:
        findings.append(SectionFinding("§2 Workflow", "PASS", n))
    elif n >= 1:
        findings.append(
            SectionFinding(
                "§2 Workflow",
                "WARN",
                n,
                (
                    "Only 1-2 ordering words found — add more ('first', 'then', "
                    "'in parallel') for higher-confidence pattern selection."
                ),
            )
        )
    else:
        findings.append(
            SectionFinding(
                "§2 Workflow",
                "BLOCK",
                0,
                (
                    "§2 has no ordering words — add 'first', 'then', 'in parallel', "
                    "'loop until', 'route to human' to describe the workflow sequence."
                ),
            )
        )

    # §5 external partners: own-system flag presence (empty may be legitimate → WARN not BLOCK)
    if sig.own_system_partners:
        findings.append(
            SectionFinding("§5 External Partners", "PASS", len(sig.own_system_partners))
        )
    else:
        findings.append(
            SectionFinding(
                "§5 External Partners",
                "WARN",
                0,
                (
                    "No 'operate their own system' flag found — if a partner runs "
                    "their own agent, mark it so A2A is chosen over MCP."
                ),
            )
        )

    # §10 acceptance criteria: ≥3 measurable PASS, 1-2 WARN, 0 BLOCK
    m = len(sig.measurable_criteria)
    if m >= 3:
        findings.append(SectionFinding("§10 Acceptance Criteria", "PASS", m))
    elif m >= 1:
        findings.append(
            SectionFinding(
                "§10 Acceptance Criteria",
                "WARN",
                m,
                (
                    "Few measurable criteria — add targets like '< 5 min', "
                    "'> 95% accuracy' to seed the golden dataset."
                ),
            )
        )
    else:
        findings.append(
            SectionFinding(
                "§10 Acceptance Criteria",
                "BLOCK",
                0,
                (
                    "§10 has no measurable criteria — add metrics like "
                    "'< 5 min' or '> 95% accuracy'."
                ),
            )
        )

    # score: PASS=full, WARN=partial, BLOCK=0 per weighted section
    weights = {
        "§2 Workflow": 50,
        "§5 External Partners": 20,
        "§10 Acceptance Criteria": 30,
    }
    score = 0
    for f in findings:
        w = weights.get(f.section, 0)
        score += w if f.status == "PASS" else (w // 2 if f.status == "WARN" else 0)

    return SpecValidation(quality_score=score, findings=findings, signals=sig)
