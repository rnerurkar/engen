"""Tests for the brownfield Epic-to-Spec front door — Phase A shaping (extractive, span-grounded) +
Phase B mapping, the Solution Accelerator Agent, and the readiness-gate reconciliation.

Run: python brownfield/tests/test_brownfield_ingest_epic.py  (or via pytest).
The agent's shaping LLM is injected via model_fn (no live Gemini), like the recommend tests.
"""

from __future__ import annotations

import json
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src")
sys.path.insert(0, _SRC)

from brownfield.ingest.orchestrator import run_ingest  # noqa: E402

EPIC = {
    "formatted_id": "E5510",
    "name": "Migrate vSphere MPA to AWS SPA",
    "description": (
        "A legacy multi-page application on Tomcat must move off vSphere. All three integrations are in "
        "scope. The UI renders with JSP on Tomcat 9 as a sync API with bidirectional traffic; it is high "
        "criticality with a hard-cutover, internal pages, session sticky state, serving 2M page views/day "
        "p95 < 800ms, targeting a SPA on CloudFront. The domain API uses an IBM API Connect 10 client as a "
        "sync API that is read-only, high criticality, dual-read, with OpenAPI 3.0, stateless, at 1M calls/"
        "day p95 < 300ms, targeting an Apigee client. Messaging uses an IBM MQ 9.1 producer as async "
        "messaging that is write-only, medium criticality, dual-write, with message contract documented, "
        "stateless, at 500K messages/day, targeting an AWS SQS producer. The business driver is to exit "
        "the on-prem datacenter."
    ),
    "nfrs": ["exit the on-prem datacenter"],
    "object_version": 22,
    "last_update_date": "2026-06-22",
}


def _f(v):  # value == verbatim span (guarantees grounding)
    return {"value": v, "epic_span": v}


def _model_fn(_system_prompt, _user_message):
    return {
        "summary": _f("A legacy multi-page application on Tomcat"),
        "modernization_scope": _f("All three integrations are in scope"),
        "integrations": [
            {
                "int_id": "INT-001",
                "name": "UI rendering",
                "fields": {
                    "technology": _f("JSP on Tomcat 9"),
                    "type": _f("sync API"),
                    "direction": _f("bidirectional"),
                    "criticality": _f("high"),
                    "coexistence": _f("hard-cutover"),
                    "api_surface": _f("internal pages"),
                    "state": _f("session sticky"),
                    "volume_sla": _f("2M page views/day p95 < 800ms"),
                },
                "target_intent": _f("SPA on CloudFront"),
            },
            {
                "int_id": "INT-002",
                "name": "Domain API",
                "fields": {
                    "technology": _f("IBM API Connect 10 client"),
                    "type": _f("sync API"),
                    "direction": _f("read-only"),
                    "criticality": _f("high"),
                    "coexistence": _f("dual-read"),
                    "api_surface": _f("OpenAPI 3.0"),
                    "state": _f("stateless"),
                    "volume_sla": _f("1M calls/day p95 < 300ms"),
                },
                "target_intent": _f("Apigee client"),
            },
            {
                "int_id": "INT-003",
                "name": "Async messaging",
                "fields": {
                    "technology": _f("IBM MQ 9.1 producer"),
                    "type": _f("async messaging"),
                    "direction": _f("write-only"),
                    "criticality": _f("medium"),
                    "coexistence": _f("dual-write"),
                    "api_surface": _f("message contract documented"),
                    "state": _f("stateless"),
                    "volume_sla": _f("500K messages/day"),
                },
                "target_intent": _f("AWS SQS producer"),
            },
        ],
        "nfrs": [
            {
                "value": "exit the on-prem datacenter",
                "kind": "nfr",
                "epic_span": "exit the on-prem datacenter",
            }
        ],
    }


def test_pipeline_and_gate():
    out = run_ingest(EPIC, model_fn=_model_fn)
    led = out["epic_signal_ledger"]
    assert (
        led["provenance"]["formatted_id"] == "E5510"
        and led["provenance"]["object_version"] == 22
    )
    assert led["schema"] == "brownfield-epic-signal-ledger/v1"
    assert len(led["integrations"]) == 3
    assert all(
        ig["filled"] == 8 and ig["confidence"] == 1.0 for ig in led["integrations"]
    )
    spec = out["spec_md"]
    assert (
        "### Integration: INT-001 — UI rendering" in spec
        and "ObjectVersion `22`" in spec
    )
    # H-3: the produced spec passes the same 8-signal readiness gate the blueprint uses.
    gate = out["blueprint_gate"]
    assert gate["blocked"] is False and gate["migration_readiness_score"] == 100
    assert gate["high_confidence_but_gated"] == []
    assert out["empty"] is False


def test_c1_fabricated_value_dropped():
    """A fabricated quantity on a real span is dropped (value-grounding)."""
    from brownfield.ingest.epic_models import Epic, EpicProvenance
    from brownfield.ingest.shaping import validate_ledger

    epic = Epic(formatted_id="E1", description="at 1M calls/day p95 < 300ms")
    mj = {
        "integrations": [
            {
                "int_id": "INT-001",
                "fields": {
                    "volume_sla": {
                        "value": "p99 < 1 millisecond",
                        "epic_span": "1M calls/day p95 < 300ms",
                    }
                },
            }
        ]
    }
    led = validate_ledger(mj, epic, EpicProvenance(formatted_id="E1"))
    vol = (
        (led.integrations[0].fields.get("volume_sla") or {}).get("value")
        if led.integrations
        else None
    )
    assert vol is None, "fabricated quantity on a real span must be dropped (C-1)"


def test_agent_structure_and_delegation():
    from brownfield.agent.solution_accelerator_agent import (
        AGENT_NAME,
        build_solution_accelerator_agent,
        delegate,
    )

    agent = build_solution_accelerator_agent()
    assert AGENT_NAME == "solution_accelerator_agent"
    assert set(agent.tools) == {"recommend_architecture", "create_epic_signal_ledger"}
    led = delegate("create_epic_signal_ledger", EPIC, model_fn=_model_fn)
    assert len(led.integrations) == 3
    # recommend_architecture routes through the agent with an injected recommend_fn
    sel = delegate(
        "recommend_architecture",
        {"substitution": {"transition_pattern_ref": "strangler-fig"}},
        model_fn=lambda sub: {
            "pattern_ref": "strangler-fig",
            "confidence": 0.9,
            "requires_review": False,
        },
    )
    assert sel["pattern_ref"] == "strangler-fig"


def test_m1_staleness_and_m4_cap():
    from brownfield.ingest.staleness import is_stale, read_provenance

    out = run_ingest(EPIC, model_fn=_model_fn)
    prov = read_provenance(spec_md="", ledger_json=out["epic_signal_ledger"])
    assert prov["formatted_id"] == "E5510" and prov["object_version"] == 22
    assert is_stale(22, 23) is True and is_stale(22, 22) is False
    try:
        run_ingest(
            {"formatted_id": "E9", "description": "x " * 30000}, model_fn=_model_fn
        )
        raise AssertionError("oversize epic should raise")
    except ValueError as e:
        assert "epic_too_large" in str(e)


if __name__ == "__main__":
    test_pipeline_and_gate()
    test_c1_fabricated_value_dropped()
    test_agent_structure_and_delegation()
    test_m1_staleness_and_m4_cap()
    out = run_ingest(EPIC, model_fn=_model_fn)
    print("OK — brownfield ingest smoke checks passed\n")
    print(
        "per_integration_confidence:",
        json.dumps(out["per_integration_confidence"], indent=2),
    )
    print("blueprint_gate:", json.dumps(out["blueprint_gate"], indent=2))
