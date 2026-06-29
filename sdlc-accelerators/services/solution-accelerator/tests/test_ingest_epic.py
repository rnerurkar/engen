"""Tests for /accelerator.ingest-epic — Phase A shaping (extractive guardrail) + Phase B mapping.

Run: python -m pytest services/solution-accelerator/tests/test_ingest_epic.py
or:  python services/solution-accelerator/tests/test_ingest_epic.py  (runs the smoke checks)

The LlmAgent is injected via model_fn (no live Gemini), exactly like the recommend_architecture tests.
"""

from __future__ import annotations

import json
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
sys.path.insert(0, _SRC)

from ingest.orchestrator import run_ingest  # noqa: E402

EPIC = {
    "formatted_id": "E2207",
    "name": "Automated FNOL intake agent",
    "description": (
        "When a claim is filed, first classify severity, then enrich from three sources in parallel. "
        "The agent reads and updates the policy database. Route high-severity claims to a human adjuster."
    ),
    "acceptance_criteria": [
        "must complete within 5 minutes at the 95th percentile",
        "severity classification accuracy above 95%",
    ],
    "nfrs": ["available 99.9% of the time"],
    "object_version": 14,
    "last_update_date": "2026-06-20",
}


def _model_fn(system_prompt: str, user_message: str) -> dict:
    """Stub LlmAgent output: mostly valid spans, plus ONE invented span that must be dropped."""
    return {
        "sections": {
            "1": [
                {
                    "value": "FNOL intake agent",
                    "kind": "use_case",
                    "epic_span": "Automated FNOL intake agent",
                }
            ],
            "2": [
                {
                    "value": "first classify severity, then enrich in parallel",
                    "kind": "ordering",
                    "epic_span": "first classify severity, then enrich from three sources in parallel",
                },
                {
                    "value": "route high-severity to a human adjuster",
                    "kind": "ordering",
                    "epic_span": "Route high-severity claims to a human adjuster",
                },
            ],
            "4": [
                {
                    "value": "Policy DB (transactional, read/write)",
                    "kind": "data_source",
                    "epic_span": "reads and updates the policy database",
                }
            ],
            "9": [
                {
                    "value": "Availability 99.9%",
                    "kind": "nfr",
                    "epic_span": "available 99.9% of the time",
                }
            ],
            "10": [
                {
                    "value": "P95 end-to-end < 5 minutes",
                    "kind": "acceptance_criterion",
                    "epic_span": "must complete within 5 minutes at the 95th percentile",
                },
                {
                    "value": "INVENTED requirement not in the epic",
                    "kind": "acceptance_criterion",
                    "epic_span": "the agent must also send a carrier pigeon notification",
                },
            ],
        }
    }


def test_pipeline_end_to_end_and_extractive_guardrail():
    out = run_ingest(EPIC, model_fn=_model_fn)
    ledger = out["epic_signal_ledger"]

    # Provenance stamped from the Epic (drives refresh drift detection).
    assert ledger["provenance"]["formatted_id"] == "E2207"
    assert ledger["provenance"]["object_version"] == 14

    by_num = {s["num"]: s for s in ledger["sections"]}

    # EXTRACTIVE GUARANTEE: the invented §10 signal (span not in the Epic) was dropped; the real one kept.
    s10_values = [sig["value"] for sig in by_num[10]["signals"]]
    assert "P95 end-to-end < 5 minutes" in s10_values
    assert all("INVENTED" not in v for v in s10_values), (
        "invented signal must be dropped"
    )

    # Phase B confidence = fill ratio (deterministic). §2 has 2/3 filled -> 0.67 -> needs review.
    assert (
        by_num[2]["filled"] == 2
        and by_num[2]["confidence"] == 0.67
        and by_num[2]["needs_review"]
    )
    # §4 has 1/2 -> 0.5 needs review; §10 has 1/3 (after drop) -> 0.33 needs review.
    assert by_num[4]["confidence"] == 0.5
    assert by_num[10]["filled"] == 1

    # Empty sections present and flagged for review (except optional §5).
    assert by_num[3]["filled"] == 0 and by_num[3]["needs_review"] is True
    assert by_num[5]["optional"] is True and by_num[5]["needs_review"] is False

    # Phase B spec.md: provenance header + a NEEDS CLARIFICATION marker for an empty section.
    spec = out["spec_md"]
    assert "Rally Epic `E2207`" in spec and "ObjectVersion" in spec and "`14`" in spec
    assert "NEEDS CLARIFICATION" in spec
    assert "## §2. Workflow Ordering" in spec and "## §10. Acceptance Criteria" in spec
    assert out["empty"] is False


def test_empty_epic_flagged():
    out = run_ingest(
        {"formatted_id": "E0", "description": ""},
        model_fn=lambda s, u: {"sections": {}},
    )
    assert out["empty"] is True


def test_solution_accelerator_agent_structure_and_delegation():
    """The MCP server delegates to ONE ADK agent that owns exactly two FunctionTools."""
    from agent.solution_accelerator_agent import (
        AGENT_NAME,
        build_solution_accelerator_agent,
        delegate,
    )

    agent = build_solution_accelerator_agent()
    assert AGENT_NAME == "solution_accelerator_agent"
    # exactly two FunctionTools: recommend_architecture + create_epic_signal_ledger
    assert set(getattr(agent, "tools", [])) == {
        "recommend_architecture",
        "create_epic_signal_ledger",
    }
    # delegate routes the ingest capability to the create_epic_signal_ledger tool
    ledger = delegate("create_epic_signal_ledger", EPIC, model_fn=_model_fn)
    assert ledger.provenance.formatted_id == "E2207"
    by_num = {s.num: s for s in ledger.sections}
    assert by_num[10].filled == 1  # invented signal still dropped via the tool path


def test_c1_fabricated_value_on_real_span_is_dropped():
    """C-1: a fabricated VALUE attached to a REAL (verbatim) span must be rejected by value-grounding."""

    def mf(_s, _u):
        return {
            "sections": {
                "10": [
                    # real span, but value invents a contradictory magnitude/unit → must be dropped
                    {
                        "value": "P99 latency under 1 millisecond",
                        "kind": "acceptance_criterion",
                        "epic_span": "must complete within 5 minutes at the 95th percentile",
                    },
                    # legitimate normalization of the same span → must be kept
                    {
                        "value": "P95 end-to-end < 5 minutes",
                        "kind": "acceptance_criterion",
                        "epic_span": "must complete within 5 minutes at the 95th percentile",
                    },
                ]
            }
        }

    out = run_ingest(EPIC, model_fn=mf)
    s10 = {s["num"]: s for s in out["epic_signal_ledger"]["sections"]}[10]
    vals = [sig["value"] for sig in s10["signals"]]
    assert "P95 end-to-end < 5 minutes" in vals
    assert all("millisecond" not in v for v in vals), (
        "fabricated value on a real span must be dropped (C-1)"
    )


def test_h3_blueprint_gate_reconciles_with_validate_spec():
    """H-3: the ingest result carries the real Step-0 gate verdict for the produced spec."""
    out = run_ingest(EPIC, model_fn=_model_fn)
    gate = out["blueprint_gate"]
    assert (
        "quality_score" in gate
        and "blocked" in gate
        and "high_confidence_but_gated" in gate
    )
    assert (
        gate["blocked"] is False
    )  # the produced spec passes the same gate the blueprint uses
    assert (
        gate["high_confidence_but_gated"] == []
    )  # no high-confidence section is secretly gated


def test_m4_oversize_epic_rejected():
    """M-4: an Epic larger than the cap is rejected with a clear error (bounded prompt surface)."""
    big = {"formatted_id": "E9", "description": "x " * 30000}
    try:
        run_ingest(big, model_fn=_model_fn)
        raise AssertionError("oversize epic should raise")
    except ValueError as e:
        assert "epic_too_large" in str(e)


def test_m1_staleness_helpers():
    """M-1: provenance read (durable ledger preferred) + ObjectVersion comparison are unit-testable."""
    from ingest.staleness import is_stale, read_provenance

    out = run_ingest(EPIC, model_fn=_model_fn)
    prov = read_provenance(
        spec_md=out["spec_md"], ledger_json=out["epic_signal_ledger"]
    )
    assert prov["formatted_id"] == "E2207" and prov["object_version"] == 14
    assert is_stale(14, 15) is True and is_stale(14, 14) is False
    # ledger is authoritative even if the (editable) spec header is gone
    assert (
        read_provenance(spec_md="", ledger_json=out["epic_signal_ledger"])[
            "object_version"
        ]
        == 14
    )


if __name__ == "__main__":
    test_pipeline_end_to_end_and_extractive_guardrail()
    test_empty_epic_flagged()
    test_solution_accelerator_agent_structure_and_delegation()
    test_c1_fabricated_value_on_real_span_is_dropped()
    test_h3_blueprint_gate_reconciles_with_validate_spec()
    test_m4_oversize_epic_rejected()
    test_m1_staleness_helpers()
    sample = run_ingest(EPIC, model_fn=_model_fn)
    print("OK — all smoke checks passed\n")
    print(
        "per_section_confidence:",
        json.dumps(sample["per_section_confidence"], indent=2),
    )
    print("blueprint_gate:", json.dumps(sample["blueprint_gate"], indent=2))
