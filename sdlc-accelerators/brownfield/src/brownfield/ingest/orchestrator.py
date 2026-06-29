"""Brownfield Epic-to-Spec ingestion orchestrator.

run_ingest(epic_payload) runs the two-phase pipeline and returns the artifacts the IDE writes:
  Phase A — the MCP server DELEGATES to the Solution Accelerator Agent's create_epic_signal_ledger
            FunctionTool (extractive, span-grounded) -> Brownfield Epic Signal Ledger
  Phase B — map_ledger_to_spec() -> integration-inventory spec.md + per-integration confidence (no LLM)

Carries the greenfield ARB fixes: blueprint_gate reconciliation (H-3), epic size cap (M-4), synchronous
phase-reporting note (L-1). In the reference impl this runs synchronously inside ingest_epic_start.
"""

from __future__ import annotations

from typing import Any

from brownfield.ingest.epic_models import Epic
from brownfield.ingest.mapping import map_ledger_to_spec

MAX_EPIC_CHARS = 50_000


def _blueprint_gate(spec_md: str, confidence: dict[str, Any]) -> dict[str, Any]:
    """H-3: run the SAME 8-signal readiness gate the brownfield blueprint uses on the produced spec,
    and flag integrations whose fill-ratio confidence is high (>= 0.85) yet do not pass the gate."""
    from brownfield.spec_parser import parse_spec
    from brownfield.validate_spec import BLOCK, WARN, validate_spec

    report = validate_spec(parse_spec(spec_md))
    findings, misaligned = [], []
    for ir in report.per_integration:
        findings.append({"integration": ir.integration_id, "status": ir.worst})
        if (
            ir.worst in (WARN, BLOCK)
            and (confidence.get(ir.integration_id, 0) or 0) >= 0.85
        ):
            misaligned.append(ir.integration_id)
    return {
        # M-2: `score` is the archetype-agnostic alias; `migration_readiness_score` kept for back-compat.
        "score": report.score,
        "migration_readiness_score": report.score,
        "blocked": report.overall == BLOCK,
        "overall": report.overall,
        "findings": findings,
        "phase_assignment_preview": report.phase_assignment_preview,
        "high_confidence_but_gated": misaligned,
    }


def run_ingest(
    epic_payload: dict[str, Any], model_fn: Any = None, on_phase: Any = None
) -> dict[str, Any]:
    """Run Phase A then Phase B. Returns
    { spec_md, epic_signal_ledger, per_integration_confidence, provenance, blueprint_gate, empty }.
    `empty` is True when the Epic yielded no integrations/summary at all.

    Note (L-1): synchronous in the reference impl — a client polling ingest_epic_status sees the terminal
    state; in production the phases ("shaping"/"mapping") run as a Cloud Run Job and are observable.
    """
    epic = Epic.from_payload(epic_payload)

    corpus = epic.raw_text()
    if len(corpus) > MAX_EPIC_CHARS:
        raise ValueError(
            f"epic_too_large: Epic body is {len(corpus)} chars (max {MAX_EPIC_CHARS}). "
            "Trim or split the Epic; ingestion shapes the Epic body, not attachments."
        )

    if on_phase:
        on_phase("shaping")
    from brownfield.agent.solution_accelerator_agent import delegate

    ledger = delegate("create_epic_signal_ledger", epic, model_fn=model_fn)

    if on_phase:
        on_phase("mapping")
    spec_md, confidence = map_ledger_to_spec(ledger)

    return {
        "spec_md": spec_md,
        "epic_signal_ledger": ledger.to_dict(),
        "per_integration_confidence": confidence,
        "provenance": ledger.provenance.to_dict(),
        "blueprint_gate": _blueprint_gate(spec_md, confidence),
        "empty": ledger.total_signals() == 0,
    }
