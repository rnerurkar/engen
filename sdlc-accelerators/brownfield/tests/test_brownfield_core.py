"""Brownfield core engines: spec/plan parsing, 8-signal gate, substitution engine, ADR predicate."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from brownfield.adr_compliance_check import (
    AdrRule,
    adr_compliance_check,
    validate_rule_tests,
)
from brownfield.adr_predicate import PredicateError, check_identifier_ceiling, evaluate
from brownfield.map_current_to_target import (
    SubstitutionRow,
    UnresolvedSubstitutionError,
    check_context_ceiling,
    map_current_to_target,
)
from brownfield.plan_parser import InvalidRFactorError, parse_plan
from brownfield.spec_parser import parse_spec
from brownfield.validate_spec import BLOCK, PASS, validate_spec

REF = ROOT / "examples/vsphere-mpa-aws-spa/inputs"


# ---------- spec parsing + 8-signal gate ----------
def test_spec_parses_four_integrations():
    spec = parse_spec((REF / "spec.md").read_text())
    assert len(spec.integrations) == 4
    assert spec.integrations[3].get("integration type") == "async messaging"


def test_validate_spec_reference_case_passes():
    report = validate_spec(parse_spec((REF / "spec.md").read_text()))
    assert report.overall == PASS
    assert report.score == 100
    assert report.phase_assignment_preview["phase_1"] == [
        "INT-003"
    ]  # read-only -> Phase 1


def test_validate_spec_blocks_on_missing_signal():
    bad = """## Integration Inventory
### Integration: INT-001 — x
- **Technology + version:** legacy system
- **Integration type:** mystery
- **Data flow direction:** sideways
- **Criticality:** unknown
- **Coexistence constraint:** maybe
- **API surface / contract:** none
- **State management:**
- **Data volume + SLA:**
### Integration: INT-002 — y
- **Technology + version:** Oracle 19c
- **Integration type:** sync api
- **Data flow direction:** read-only
- **Criticality:** high
- **Coexistence constraint:** dual-read
- **API surface / contract:** OpenAPI
- **State management:** stateless
- **Data volume + SLA:** 1M/day
### Integration: INT-003 — z
- **Technology + version:** IBM MQ 9.1
- **Integration type:** async messaging
- **Data flow direction:** write-only
- **Criticality:** medium
- **Coexistence constraint:** dual-write
- **API surface / contract:** none
- **State management:** stateless
- **Data volume + SLA:** 500K/day
"""
    report = validate_spec(parse_spec(bad))
    assert report.overall == BLOCK  # INT-001 has multiple BLOCK signals


# ---------- plan parsing ----------
def test_plan_parses_r_factors():
    plan = parse_plan((REF / "plan.md").read_text())
    assert len(plan) == 4
    assert {d.r_factor for d in plan} == {"refactor", "replatform"}


def test_plan_rejects_invalid_r_factor():
    import pytest

    bad = "### Integration: INT-001 — x\n- **R-factor:** teleport\n"
    with pytest.raises(InvalidRFactorError):
        parse_plan(bad)


# ---------- substitution engine ----------
def _ref_rows():
    table = json.loads((REF / "substitution-table.json").read_text())
    return [SubstitutionRow(**r) for r in table["rows"]]


def _ref_integrations():
    spec = parse_spec((REF / "spec.md").read_text())
    plan = {d.integration_id: d for d in parse_plan((REF / "plan.md").read_text())}
    return [
        {
            "integration_id": it.integration_id,
            "source_tech": it.get("technology + version"),
            "r_factor": plan[it.integration_id].r_factor,
            "context": plan[it.integration_id].context,
        }
        for it in spec.integrations
    ]


def test_substitution_resolves_reference_case():
    result = map_current_to_target(_ref_integrations(), _ref_rows())
    assert len(result["tech_substitutions"]) == 4
    assert result["unresolved"] == []
    mq = next(
        s for s in result["tech_substitutions"] if s["integration_id"] == "INT-004"
    )
    assert "aws-sqs" in mq["target_tokens"]
    assert mq["transition_pattern_ref"] == "PAT-T-007-dual-publish-mq-sqs"


def test_substitution_token_normalization():
    # 'IBM API Connect' (spaces) must match row token 'ibm-api-connect' (hyphens)
    result = map_current_to_target(_ref_integrations(), _ref_rows())
    apic = next(
        s for s in result["tech_substitutions"] if s["integration_id"] == "INT-003"
    )
    assert "apigee" in apic["target_tokens"]


def test_substitution_unresolved_errors():
    import pytest

    rows = _ref_rows()
    ints = [
        {
            "integration_id": "INT-099",
            "source_tech": "COBOL on z/OS",
            "r_factor": "rehost",
            "context": {},
        }
    ]
    with pytest.raises(UnresolvedSubstitutionError) as e:
        map_current_to_target(ints, rows)
    assert "INT-099" in str(e.value)


def test_substitution_most_specific_wins():
    rows = [
        SubstitutionRow(["ibm-mq"], "refactor", {}, ["sqs-generic"], priority=1),
        SubstitutionRow(
            ["ibm-mq"],
            "refactor",
            {"messaging_pattern": "point-to-point"},
            ["sqs-p2p"],
            priority=1,
        ),
    ]
    ints = [
        {
            "integration_id": "I1",
            "source_tech": "IBM MQ 9.1",
            "r_factor": "refactor",
            "context": {"messaging_pattern": "point-to-point"},
        }
    ]
    result = map_current_to_target(ints, rows)
    assert result["tech_substitutions"][0]["target_tokens"] == [
        "sqs-p2p"
    ]  # more specific row wins


def test_substitution_tie_flags_review():
    rows = [
        SubstitutionRow(["ibm-mq"], "refactor", {}, ["a"], priority=1),
        SubstitutionRow(["ibm-mq"], "refactor", {}, ["b"], priority=1),
    ]
    ints = [
        {
            "integration_id": "I1",
            "source_tech": "IBM MQ",
            "r_factor": "refactor",
            "context": {},
        }
    ]
    result = map_current_to_target(ints, rows)
    assert result["tech_substitutions"][0]["requires_review"] is True


def test_context_ceiling_enforced():
    import pytest

    over = SubstitutionRow(["x"], "rehost", {f"d{i}": "v" for i in range(13)}, ["y"])
    with pytest.raises(ValueError):
        check_context_ceiling([over])


# ---------- ADR predicate interpreter ----------
def test_predicate_documented_examples():
    assert (
        evaluate(
            "target_tech == 'aurora-mysql' AND data_size_gb > 10000",
            {"target_tech": "aurora-mysql", "data_size_gb": 15000},
        )
        is True
    )
    assert (
        evaluate(
            "cross_cloud_egress AND target_gateway != 'apigee'",
            {"cross_cloud_egress": True, "target_gateway": "apigee"},
        )
        is False
    )


def test_predicate_not_and_parens():
    assert evaluate("NOT (a == 'x' OR b == 'y')", {"a": "z", "b": "w"}) is True


def test_predicate_no_eval_rejects_garbage():
    import pytest

    with pytest.raises(PredicateError):
        evaluate("__import__('os').system('ls')", {})


def test_identifier_ceiling():
    import pytest

    expr = " AND ".join(f"id{i} == 'v'" for i in range(26))
    with pytest.raises(PredicateError):
        check_identifier_ceiling(expr)


# ---------- ADR compliance check ----------
def _rule(adr, pred, action):
    return AdrRule(
        adr_id=adr,
        key={
            "source_tech": "*",
            "target_tech": "*",
            "functional_category": "*",
            "r_factor": "*",
        },
        predicate=pred,
        action=action,
    )


def test_adr_reject_dominates():
    rules = [
        _rule("ADR-118", "data_size_gb > 10000", "REJECT"),
        _rule("ADR-403", "criticality == 'tier1'", "FLAG"),
    ]
    res = adr_compliance_check(
        "INT-1",
        {
            "source_tech": "x",
            "target_tech": "y",
            "functional_category": "z",
            "r_factor": "refactor",
        },
        {"data_size_gb": 20000, "criticality": "tier1"},
        rules,
    )
    assert res.result == "reject"
    assert "ADR-118" in res.violations


def test_adr_pass_when_no_predicate_trips():
    rules = [_rule("ADR-118", "data_size_gb > 10000", "REJECT")]
    res = adr_compliance_check(
        "INT-1",
        {
            "source_tech": "x",
            "target_tech": "y",
            "functional_category": "z",
            "r_factor": "refactor",
        },
        {"data_size_gb": 500},
        rules,
    )
    assert res.result == "pass"
    assert res.attested_adrs[0]["result"] == "pass"


def test_validate_rule_tests_requires_three_each():
    import pytest

    rule = AdrRule(
        "ADR-X",
        {},
        "data_size_gb > 100",
        "REJECT",
        tests={"positive": [{"data_size_gb": 200}], "negative": [{"data_size_gb": 50}]},
    )
    with pytest.raises(ValueError):
        validate_rule_tests(rule)  # only 1 each, needs 3
