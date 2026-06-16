"""Dedicated unit tests for assemble_blueprint: four-diagram generation, cross-cloud Phase-0,
contract v2.0 shape, per-integration blocks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from brownfield.assemble_blueprint import CROSS_CLOUD_TOKENS, assemble_blueprint
from brownfield.plan_parser import parse_plan
from brownfield.spec_parser import parse_spec

REF = ROOT / "examples/vsphere-mpa-aws-spa/inputs"


def _fixtures():
    spec = parse_spec((REF / "spec.md").read_text())
    plan = parse_plan((REF / "plan.md").read_text())
    subs = [
        {"integration_id": "INT-003", "source_tokens": ["apic"], "r_factor": "replatform",
         "target_tokens": ["apigee", "privatelink"], "transition_pattern_ref": "PAT-T-009",
         "context_matched": {}},
        {"integration_id": "INT-004", "source_tokens": ["ibm-mq"], "r_factor": "refactor",
         "target_tokens": ["aws-sqs"], "transition_pattern_ref": "PAT-T-007", "context_matched": {}},
    ]
    sels = [{"integration_id": s["integration_id"], "pattern_ref": s["transition_pattern_ref"],
             "confidence": 0.9} for s in subs]
    adrs = [{"integration_id": "INT-003", "adr_id": "ADR-101", "result": "pass"}]
    return spec, plan, subs, sels, adrs


def test_assemble_produces_four_diagrams():
    spec, plan, subs, sels, adrs = _fixtures()
    out = assemble_blueprint(spec, subs, sels, adrs, plan, readiness_score=100)
    names = {d["name"] for d in out.diagrams}
    assert names == {"component-end-state", "sequence-end-state", "sequence-transition", "infrastructure"}


def test_cross_cloud_phase0_injected_when_privatelink():
    spec, plan, subs, sels, adrs = _fixtures()
    out = assemble_blueprint(spec, subs, sels, adrs, plan, readiness_score=100)
    phase0 = [p for p in out.design_contract["migration_phases"] if p["phase"] == 0]
    assert len(phase0) == 1
    assert "INT-003" in phase0[0]["integration_ids"]
    assert any(t in CROSS_CLOUD_TOKENS for t in subs[0]["target_tokens"])


def test_no_phase0_without_cross_cloud():
    spec, plan, subs, sels, adrs = _fixtures()
    subs = [s for s in subs if s["integration_id"] == "INT-004"]   # no cross-cloud
    sels = [s for s in sels if s["integration_id"] == "INT-004"]
    out = assemble_blueprint(spec, subs, sels, adrs, plan, readiness_score=100)
    assert all(p["phase"] != 0 for p in out.design_contract["migration_phases"])


def test_contract_is_v2_live_with_substitutions():
    spec, plan, subs, sels, adrs = _fixtures()
    c = assemble_blueprint(spec, subs, sels, adrs, plan, 100).design_contract
    assert c["schema_version"] == "2.0" and c["lifecycle"] == "LIVE"
    assert len(c["tech_substitutions"]) == 2
    assert "staleness_triggers" in c


def test_markdown_has_block_per_integration_with_rollback():
    spec, plan, subs, sels, adrs = _fixtures()
    md = assemble_blueprint(spec, subs, sels, adrs, plan, 100).markdown
    assert "### INT-003" in md and "### INT-004" in md
    assert "Rollback:" in md
