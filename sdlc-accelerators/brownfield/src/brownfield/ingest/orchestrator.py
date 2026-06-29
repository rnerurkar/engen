"""Brownfield /accelerator.epic-to-spec orchestrator.

run_epic_to_spec(epic_payload, csa_architecture_md) runs the three-phase pipeline and returns the
artifacts the IDE writes:

  Phase A — RESOLVE & VALIDATE (deterministic): parse the Epic's Modernization Scope table, load the
            upstream CSA registry from architecture.md, and cross-walk every Epic-named component ID
            against the CSA. Unresolved IDs block (you cannot modernize what the current state lacks).
  Phase B — COMPOSE (deterministic in the fusion path): render the canonical specify-conformant spec.md
            — per-component modernization units (Refactor|Rehost + AWS target) plus the CSA-sourced
            8-signal Integration Inventory that `/speckit.plan` and the readiness gate consume unchanged.
  Phase C — GATE & TRACE (deterministic): score the spec with the SAME validate_spec gate, emit the
            modernization-scope ledger (component -> disposition -> target -> source spans), and stamp
            provenance for BOTH sources (Epic FormattedID+ObjectVersion AND the CSA architecture.md hash).

When no CSA architecture.md is supplied, the pipeline degrades to the LEGACY extractive path (Epic-only
LLM shaping -> integration inventory); the spec tells the developer to supply the CSA or use
/speckit.specify. This keeps the front door usable before a CSA exists.

In the reference impl this runs synchronously inside the MCP `epic_to_spec_start` handler.
"""

from __future__ import annotations

from typing import Any

from brownfield.ingest.csa_loader import load_csa
from brownfield.ingest.epic_models import Epic
from brownfield.ingest.fusion import cross_walk
from brownfield.ingest.mapping import compose_spec, map_ledger_to_spec

MAX_EPIC_CHARS = 50_000


def _blueprint_gate(spec_md: str, confidence: dict[str, Any]) -> dict[str, Any]:
    """Run the SAME 8-signal readiness gate the brownfield blueprint uses on the produced spec, and
    flag integrations whose fill-ratio confidence is high (>= 0.85) yet do not pass the gate."""
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
        # `score` is the archetype-agnostic alias; `migration_readiness_score` kept for back-compat.
        "score": report.score,
        "migration_readiness_score": report.score,
        "blocked": report.overall == BLOCK,
        "overall": report.overall,
        "findings": findings,
        "phase_assignment_preview": report.phase_assignment_preview,
        "high_confidence_but_gated": misaligned,
    }


def _legacy_path(epic: Epic, model_fn: Any, on_phase: Any) -> dict[str, Any]:
    """Epic-only extractive fallback (no CSA). Mirrors the pre-redesign behavior."""
    if on_phase:
        on_phase("shaping")
    from brownfield.agent.solution_accelerator_agent import delegate

    ledger = delegate("create_epic_signal_ledger", epic, model_fn=model_fn)
    if on_phase:
        on_phase("mapping")
    spec_md, confidence = map_ledger_to_spec(ledger)
    return {
        "mode": "legacy-extractive",
        "spec_md": spec_md,
        "epic_signal_ledger": ledger.to_dict(),
        "modernization_scope_ledger": None,
        "per_integration_confidence": confidence,
        "per_component_confidence": {},
        "resolved_scope": None,
        "provenance": ledger.provenance.to_dict(),
        "blueprint_gate": _blueprint_gate(spec_md, confidence),
        "empty": ledger.total_signals() == 0,
    }


def run_epic_to_spec(
    epic_payload: dict[str, Any],
    csa_architecture_md: str = "",
    model_fn: Any = None,
    on_phase: Any = None,
) -> dict[str, Any]:
    """Run the Epic-to-Spec pipeline. Returns the IDE artifacts (spec_md, ledgers, gate, provenance).

    Fusion path (CSA present + Epic scope table): deterministic, no LLM. Legacy path (no CSA): extractive.
    """
    epic = Epic.from_payload(epic_payload)

    corpus = epic.raw_text()
    if len(corpus) > MAX_EPIC_CHARS:
        raise ValueError(
            f"epic_too_large: Epic body is {len(corpus)} chars (max {MAX_EPIC_CHARS}). "
            "Trim or split the Epic; ingestion shapes the Epic body, not attachments."
        )

    registry = load_csa(csa_architecture_md)

    # Fusion path requires a CSA with components AND an Epic that declares a scope table.
    if registry.components and epic.scope_items:
        if on_phase:
            on_phase("resolving")
        rs = cross_walk(epic.scope_items, registry)
        if on_phase:
            on_phase("composing")
        spec_md, comp_conf, scope_ledger = compose_spec(
            epic, registry, rs, csa_hash=registry.content_hash
        )
        if on_phase:
            on_phase("gating")
        return {
            "mode": "fusion",
            "spec_md": spec_md,
            "modernization_scope_ledger": scope_ledger,
            "epic_signal_ledger": None,
            "resolved_scope": rs.to_dict(),
            "per_component_confidence": comp_conf,
            "per_integration_confidence": {},
            "provenance": epic.provenance(csa_hash=registry.content_hash).to_dict(),
            "blueprint_gate": _blueprint_gate(spec_md, {}),
            "scope_blocked": rs.blocked,
            "empty": not rs.in_scope,
        }

    return _legacy_path(epic, model_fn, on_phase)


def run_ingest(
    epic_payload: dict[str, Any],
    csa_architecture_md: str = "",
    model_fn: Any = None,
    on_phase: Any = None,
) -> dict[str, Any]:
    """Back-compat alias for run_epic_to_spec (the command was renamed from ingest-epic)."""
    return run_epic_to_spec(
        epic_payload,
        csa_architecture_md=csa_architecture_md,
        model_fn=model_fn,
        on_phase=on_phase,
    )
