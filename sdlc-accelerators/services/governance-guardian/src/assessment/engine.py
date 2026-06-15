"""Governance Guardian assessment engine.

The scoring rubric, the per-section EA criteria, and the showstopper-vs-tech-debt
classification are HUMAN-AUTHORED EA IP. This module provides the runnable harness
(task lifecycle, scorecard structure, finding classification flow) and a clearly-
marked extension point `assess_sections()` for the EA team to implement.

Per root CLAUDE.md, the platform build does NOT fabricate the assessment logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["critical", "high", "medium", "low"]
Classification = Literal["showstopper", "tech_debt"]


@dataclass
class Finding:
    id: str
    severity: Severity
    classification: Classification
    section: str
    message: str


@dataclass
class Scorecard:
    overall: float
    per_section: dict[int, float] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    @property
    def has_showstopper(self) -> bool:
        return any(f.classification == "showstopper" for f in self.findings)

    def resume_signal(self) -> str:
        return "stop" if self.has_showstopper else "resume"


def assess_sections(sections: dict[int, str]) -> Scorecard:
    """HUMAN-AUTHORED. The EA team implements the rubric here.

    Until implemented, this raises — the harness is runnable, the judgment is not faked.
    A reference implementation would: score each §1-§9 against EA criteria, classify
    findings, and aggregate a weighted overall score.
    """
    raise NotImplementedError(
        "Governance Guardian assessment rubric is human-authored EA IP. "
        "Implement scoring/classification here per the EA standards."
    )


def classify_finding(severity: Severity) -> Classification:
    """The ONE piece of classification policy that is platform-level, not EA judgment:
    critical severity is always a showstopper. Everything else defaults to tech_debt
    unless the EA rubric overrides. The EA team refines this in assess_sections()."""
    return "showstopper" if severity == "critical" else "tech_debt"
