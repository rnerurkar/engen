"""Epic-to-Spec ingestion orchestrator.

run_ingest(epic_payload) executes the two-phase pipeline and returns the artifacts the IDE writes:
  Phase A — shape_epic()        -> Epic Signal Ledger (the one LlmAgent, extractive)
  Phase B — map_ledger_to_spec() -> spec.md + per-section confidence (deterministic)

Mirrors pipeline.orchestrator.run_pipeline (blueprint) in shape: the server's ingest_epic_start runs this
synchronously in the reference implementation; in production it runs as a Cloud Run Job via Cloud Tasks,
with status reported as phase = "shaping" -> "mapping".

The epic payload is CONTENT ONLY (the coding agent fetched it client-side via the Rally MCP server using
the developer's Entra ID SSO). No Rally credentials are accepted or required here.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ingest.epic_models import Epic
from ingest.mapping import map_ledger_to_spec

# M-4: bound the Epic that gets concatenated into the shaping prompt (prompt-injection / DoS surface).
# Span-grounding in Phase A is the PRIMARY mitigation; this cap is defense-in-depth.
MAX_EPIC_CHARS = 50_000


def _sec_num(label: Any) -> int | None:
    m = re.match(r"\s*§?\s*(\d+)", str(label))
    return int(m.group(1)) if m else None


def _blueprint_gate(spec_md: str, confidence: dict[str, Any]) -> dict[str, Any]:
    """H-3: run the SAME Step-0 quality gate the blueprint uses (`validate_spec`) on the produced spec,
    and flag any section whose fill-ratio confidence is high (>= 0.85) yet does NOT satisfy the gate.

    This reconciles the two quality models: the IDE can surface the real blueprint-readiness of the
    ingested spec instead of fill-ratio confidence alone (which measures a different thing).
    """
    from reasoning.validate_spec import validate_spec

    v = validate_spec(spec_md)
    conf_by_num = {_sec_num(k): val for k, val in (confidence or {}).items()}
    findings, misaligned = [], []
    for f in v.findings:
        findings.append({"section": f.section, "status": f.status})
        if (
            f.status in ("WARN", "BLOCK")
            and (conf_by_num.get(_sec_num(f.section), 0) or 0) >= 0.85
        ):
            misaligned.append(f.section)
    return {
        # M-2: `score` is the archetype-agnostic alias; `quality_score` kept for back-compat.
        "score": v.quality_score,
        "quality_score": v.quality_score,
        "blocked": v.blocked,
        "findings": findings,
        "high_confidence_but_gated": misaligned,
    }


def run_ingest(
    epic_payload: dict[str, Any], model_fn: Any = None, on_phase: Any = None
) -> dict[str, Any]:
    """Run Phase A then Phase B. `on_phase(name)` is an optional progress hook ("shaping"/"mapping").

    Returns: { spec_md, epic_signal_ledger, per_section_confidence, provenance, blueprint_gate, empty }.
    `empty` is True when the Epic yielded no signals at all (caller surfaces an actionable failure).
    `blueprint_gate` is the Step-0 `validate_spec` verdict for the produced spec (H-3 reconciliation).

    Note (L-1): in the reference implementation this runs synchronously inside `ingest_epic_start`, so a
    client polling `ingest_epic_status` observes the terminal state rather than intermediate phases; in
    production the phases run as a Cloud Run Job and `phase` ("shaping"/"mapping") is observable.
    """
    epic = Epic.from_payload(epic_payload)

    corpus = epic.raw_text()
    if len(corpus) > MAX_EPIC_CHARS:
        raise ValueError(
            f"epic_too_large: Epic body is {len(corpus)} chars (max {MAX_EPIC_CHARS}). "
            "Trim or split the Epic; ingestion shapes the Epic body, not attachments."
        )

    # Phase A — the MCP server DELEGATES to the Solution Accelerator Agent (ADK), running its
    # create_epic_signal_ledger FunctionTool (extractive, span-grounded shaping → Epic Signal Ledger).
    if on_phase:
        on_phase("shaping")
    from agent.solution_accelerator_agent import delegate

    ledger = delegate("create_epic_signal_ledger", epic, model_fn=model_fn)

    if on_phase:
        on_phase("mapping")
    spec_md, confidence = map_ledger_to_spec(ledger)  # Phase B — deterministic mapping

    total_signals = sum(s.filled for s in ledger.sections)
    return {
        "spec_md": spec_md,
        "epic_signal_ledger": ledger.to_dict(),
        "per_section_confidence": confidence,
        "provenance": ledger.provenance.to_dict(),
        "blueprint_gate": _blueprint_gate(spec_md, confidence),
        "empty": total_signals == 0,
    }
