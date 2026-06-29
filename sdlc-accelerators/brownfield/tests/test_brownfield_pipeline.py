"""Brownfield pipeline + assembly + generation end-to-end on the reference case."""

import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from brownfield.generator import check_rollback_paths, generate_migration_code
from brownfield.map_current_to_target import SubstitutionRow
from brownfield.pipeline import MigrationReadinessBlocked, run_brownfield_pipeline
from brownfield.plan_parser import parse_plan
from brownfield.spec_parser import parse_spec

REF = ROOT / "examples/vsphere-mpa-aws-spa"


def _rows():
    return [
        SubstitutionRow(**r)
        for r in json.loads((REF / "inputs/substitution-table.json").read_text())[
            "rows"
        ]
    ]


def _recommend(sub):
    return {
        "pattern_ref": sub["transition_pattern_ref"],
        "confidence": 0.9,
        "requires_review": False,
    }


def _run():
    return run_brownfield_pipeline(
        (REF / "inputs/spec.md").read_text(),
        (REF / "inputs/plan.md").read_text(),
        _rows(),
        adr_rules=[],
        recommend_fn=_recommend,
    )


def test_pipeline_completes_reference_case():
    r = _run()
    assert r["readiness"]["score"] == 100
    assert len(r["design_contract"]["tech_substitutions"]) == 4


def test_contract_is_v2_live():
    c = _run()["design_contract"]
    assert c["schema_version"] == "2.0"
    assert c["lifecycle"] == "LIVE"


def test_cross_cloud_phase0_injected():
    phases = _run()["design_contract"]["migration_phases"]
    phase0 = [p for p in phases if p["phase"] == 0]
    assert len(phase0) == 1
    assert phase0[0]["cross_cloud_coordination"] is True
    assert "INT-003" in phase0[0]["integration_ids"]


def test_four_diagrams_generated():
    diagrams = _run()["diagrams"]
    names = {d["name"] for d in diagrams}
    assert names == {
        "component-end-state",
        "sequence-end-state",
        "sequence-transition",
        "infrastructure",
    }


def test_contract_validates_against_schema():
    import jsonschema

    schema = json.loads((ROOT / "schemas/design-contract.schema.json").read_text())
    schema["properties"]["tech_substitutions"]["items"] = {"type": "object"}
    jsonschema.validate(_run()["design_contract"], schema)


def test_readiness_block_raises():
    bad_spec = """## Integration Inventory
### Integration: INT-001 — x
- **Technology + version:**
- **Integration type:** nonsense
- **Data flow direction:** nonsense
- **Criticality:** nonsense
- **Coexistence constraint:** nonsense
- **API surface / contract:** none
- **State management:**
- **Data volume + SLA:**
"""
    import pytest

    with pytest.raises(MigrationReadinessBlocked):
        run_brownfield_pipeline(
            bad_spec,
            "### Integration: INT-001 — x\n- **R-factor:** refactor\n",
            _rows(),
            adr_rules=[],
            recommend_fn=_recommend,
        )


def test_generation_per_strategy_with_rollback():
    spec = parse_spec((REF / "inputs/spec.md").read_text())
    plan = parse_plan((REF / "inputs/plan.md").read_text())
    contract = _run()["design_contract"]
    with tempfile.TemporaryDirectory() as d:
        result = generate_migration_code(
            contract, plan, spec, str(ROOT / "templates/code/brownfield-migration"), d
        )
        assert result["count"] == 4
        # INT-004 dual-publish -> dual_write template
        int4 = (Path(d) / "migrations/int_004_migration.py").read_text()
        assert "Dual-write window" in int4
        # INT-002 strangler-fig -> strangler proxy
        int2 = (Path(d) / "migrations/int_002_migration.py").read_text()
        assert "Strangler-Fig proxy" in int2
        # every file has a rollback path (constitution)
        assert check_rollback_paths(d) == []


def test_prs_flags_missing_rollback():
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "migrations").mkdir()
        (Path(d) / "migrations/bad_migration.py").write_text(
            "# no rollback here\ndef route(): pass\n"
        )
        violations = check_rollback_paths(d)
        assert len(violations) == 1
