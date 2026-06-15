"""EvalOps Phase 1 — automated evaluation gate (Constitution Rules 11-12).

Runs the golden dataset against the agent and computes pass/fail vs the threshold.
The gate LOGIC is real and tested; the Vertex AI Evaluation SDK call is stubbed
(marked TODO) for live wiring. This is the gate the Production Readiness check and
the Harness pipeline consult before AgentEngine deploy.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalResult:
    score: float
    threshold: float
    passed: bool
    per_metric: dict
    entries_evaluated: int


def load_golden_dataset(path: str) -> list[dict]:
    """Golden dataset seeded from spec §10 (Constitution Rule 12)."""
    data = json.loads(Path(path).read_text())
    return data.get("entries", data) if isinstance(data, dict) else data


def run_phase1(golden_path: str, threshold: float = 0.90) -> EvalResult:
    """Run Phase-1 automated metrics and gate on the threshold.

    TODO(live): replace the stubbed scoring with Vertex AI Evaluation SDK
    (PointwiseMetric / AutoSxS). The gate logic below is production-ready.
    """
    entries = load_golden_dataset(golden_path)
    if not entries:
        return EvalResult(0.0, threshold, False, {}, 0)

    # STUB scoring — live: call Vertex AI Eval SDK per entry, aggregating
    # per-metric scores (exact_match, groundedness, safety) then gating on threshold.
    # The structure (per-metric aggregation + threshold gate) is the real contract.
    raise NotImplementedError(
        f"Loaded {len(entries)} golden entries. Wire Vertex AI Evaluation SDK to score "
        f"them (threshold {threshold:.2f}). Gate logic is ready."
    )


def gate(result: EvalResult) -> int:
    """Exit code for the pipeline: 0 if eval passes, 1 if below threshold."""
    return 0 if result.passed else 1
