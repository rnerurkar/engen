"""validate_spec — 8-signal brownfield migration-readiness gate.

Deterministic. For each integration, checks the eight signals; each yields PASS/WARN/BLOCK.
Produces a migration_readiness_score (0-100) and a phase_assignment_preview. Any BLOCK signal
makes the overall result BLOCK (blueprint_start returns immediately with guidance).

Brownfield validation prevents data loss in a running production system — it is stricter than
greenfield's "do we have enough to compose an architecture?".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .spec_parser import BrownfieldSpec, Integration

PASS, WARN, BLOCK = "PASS", "WARN", "BLOCK"

VALID_TYPES = {"sync api", "async messaging", "batch", "db link", "file transfer"}
VALID_DIRECTION = {"read-only", "write-only", "bidirectional"}
VALID_CRIT = {"critical", "high", "medium", "low"}
VALID_COEXIST = {"dual-read", "dual-write", "hard-cutover", "n/a"}
VAGUE_TECH = {
    "legacy",
    "messaging system",
    "database",
    "the system",
    "old system",
    "various",
}


@dataclass
class SignalResult:
    signal: str
    status: str
    detail: str = ""


@dataclass
class IntegrationReadiness:
    integration_id: str
    signals: list[Any] = field(default_factory=list)

    @property
    def worst(self) -> str:
        order = {PASS: 0, WARN: 1, BLOCK: 2}
        return max(
            (s.status for s in self.signals), key=lambda s: order[s], default=PASS
        )


@dataclass
class ReadinessReport:
    per_integration: list[Any] = field(default_factory=list)
    score: int = 0
    overall: str = PASS
    phase_assignment_preview: dict[str, Any] = field(default_factory=dict)


def _has(v: str) -> bool:
    return bool(v and v.strip())


def _check_integration(it: Integration) -> IntegrationReadiness:
    """Evaluate all eight readiness signals for one integration."""
    r = IntegrationReadiness(integration_id=it.integration_id)
    tech = it.get("technology + version").lower()
    # 1. CSA Completeness
    if not _has(tech):
        r.signals.append(
            SignalResult("CSA Completeness", BLOCK, "no technology+version")
        )
    elif any(v in tech for v in VAGUE_TECH) and not any(ch.isdigit() for ch in tech):
        r.signals.append(SignalResult("CSA Completeness", WARN, "vague technology"))
    else:
        r.signals.append(SignalResult("CSA Completeness", PASS))
    # 2. Integration Type
    t = it.get("integration type").lower()
    r.signals.append(
        SignalResult("Integration Type", PASS if t in VALID_TYPES else BLOCK, t)
    )
    # 3. Data Flow Direction
    d = it.get("data flow direction").lower()
    r.signals.append(
        SignalResult("Data Flow Direction", PASS if d in VALID_DIRECTION else BLOCK, d)
    )
    # 4. Criticality
    c = it.get("criticality").lower()
    r.signals.append(
        SignalResult("Criticality Rating", PASS if c in VALID_CRIT else BLOCK, c)
    )
    # 5. Coexistence
    co = it.get("coexistence constraint").lower()
    r.signals.append(
        SignalResult(
            "Coexistence Constraints", PASS if co in VALID_COEXIST else BLOCK, co
        )
    )
    # 6. API Surface
    api = it.get("api surface / contract").lower()
    if not _has(api):
        r.signals.append(SignalResult("API Surface", WARN, "unspecified"))
    elif "none" in api and "external" in t:
        r.signals.append(
            SignalResult("API Surface", BLOCK, "external API without contract")
        )
    else:
        r.signals.append(SignalResult("API Surface", PASS))
    # 7. State Management
    st = it.get("state management").lower()
    r.signals.append(SignalResult("State Management", PASS if _has(st) else BLOCK, st))
    # 8. Data Volume + SLA
    vol = it.get("data volume + sla").lower()
    r.signals.append(
        SignalResult("Data Volume + SLA", PASS if _has(vol) else BLOCK, vol)
    )
    return r


def _phase_of(it: Integration) -> int:
    """Phase assignment: read-only -> Phase 1; write/bidirectional -> Phase 2; retire -> Phase 3."""
    d = it.get("data flow direction").lower()
    if d == "read-only":
        return 1
    return 2


def validate_spec(spec: BrownfieldSpec) -> ReadinessReport:
    """Run the 8-signal migration-readiness gate. Returns a ReadinessReport with per-signal
    status, a 0-100 score, the overall PASS/WARN/BLOCK verdict, and a phase-assignment preview."""
    report = ReadinessReport()
    if len(spec.integrations) < 3:
        # CSA diagram missing or <3 integrations -> CSA Completeness BLOCK at the spec level.
        report.overall = BLOCK
    total_signals, pass_signals = 0, 0
    phases: dict[int, list[Any]] = {1: [], 2: [], 3: []}
    for it in spec.integrations:
        ir = _check_integration(it)
        report.per_integration.append(ir)
        for s in ir.signals:
            total_signals += 1
            if s.status == PASS:
                pass_signals += 1
            if s.status == BLOCK:
                report.overall = BLOCK
        phases[_phase_of(it)].append(it.integration_id)
    report.score = round(100 * pass_signals / total_signals) if total_signals else 0
    report.phase_assignment_preview = {f"phase_{k}": v for k, v in phases.items()}
    if report.overall != BLOCK and any(
        ir.worst == WARN for ir in report.per_integration
    ):
        report.overall = WARN
    return report
