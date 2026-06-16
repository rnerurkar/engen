"""Real-execution tests for the brownfield orchestrator deterministic steps (1a).

Drives each BaseAgent step's _run_async_impl with a minimal fake InvocationContext that carries
session.state, proving the steps actually run the tested pipeline functions (not stubs)."""
import asyncio
import json
import types
from pathlib import Path

from brownfield.map_current_to_target import SubstitutionRow
from brownfield.orchestrator.adk_steps import (
    AdrComplianceStep,
    AssembleContractStep,
    MigrationReadinessStep,
    SubstitutionStep,
)

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "examples/vsphere-mpa-aws-spa/inputs"


class _FakeSession:
    def __init__(self, state):
        self.state = state


class _FakeCtx:
    """Minimal stand-in for InvocationContext exposing .session.state."""
    def __init__(self, state):
        self.session = _FakeSession(state)


def _drain(step, state):
    """Run a step's async generator to completion against a fake context; return final state."""
    ctx = _FakeCtx(state)

    async def go():
        events = []
        async for ev in step._run_async_impl(ctx):
            events.append(ev)
        return events
    asyncio.run(go())
    return state


def _seed_state():
    rows = json.loads((REF / "substitution-table.json").read_text())["rows"]
    return {
        "spec_md": (REF / "spec.md").read_text(),
        "plan_md": (REF / "plan.md").read_text(),
        "substitution_rows": [SubstitutionRow(**r) for r in rows],
        "adr_rules": [],
    }


def test_readiness_step_runs_real_validate_spec():
    state = _drain(MigrationReadinessStep(name="brownfield_migration_readiness"), _seed_state())
    assert state["readiness"]["score"] == 100          # real validate_spec output
    assert state["readiness"]["overall"] == "PASS"
    assert "spec" in state and "plan" in state


def test_substitution_step_runs_real_map_current_to_target():
    state = _seed_state()
    _drain(MigrationReadinessStep(name="r"), state)
    _drain(SubstitutionStep(name="brownfield_substitution"), state)
    assert len(state["substitutions"]) == 4            # real substitution output
    mq = next(s for s in state["substitutions"] if s["integration_id"] == "INT-004")
    assert "aws-sqs" in mq["target_tokens"]


def test_full_deterministic_chain_assembles_real_contract():
    """Run readiness → substitution → ADR → assemble (the LLM step is skipped; assembly falls back
    to substitution transition refs). Proves the deterministic chain produces a real contract."""
    state = _seed_state()
    for step in (MigrationReadinessStep(name="r"), SubstitutionStep(name="s"),
                 AdrComplianceStep(name="a"), AssembleContractStep(name="asm")):
        _drain(step, state)
    contract = state["design_contract"]
    assert contract["schema_version"] == "2.0"
    assert contract["lifecycle"] == "LIVE"
    assert len(contract["tech_substitutions"]) == 4
    assert len(state["diagrams"]) == 4
    # cross-cloud Phase-0 injected for INT-003 (real assemble_blueprint logic)
    assert any(p["phase"] == 0 for p in contract["migration_phases"])


def test_readiness_block_halts_chain():
    bad = {"spec_md": """## Integration Inventory
### Integration: INT-001 — x
- **Technology + version:**
- **Integration type:** nope
- **Data flow direction:** nope
- **Criticality:** nope
- **Coexistence constraint:** nope
- **API surface / contract:** none
- **State management:**
- **Data volume + SLA:**
""", "plan_md": "### Integration: INT-001 — x\n- **R-factor:** refactor\n",
           "substitution_rows": [], "adr_rules": []}
    state = _drain(MigrationReadinessStep(name="r"), bad)
    assert state.get("_blocked") is True
    # downstream steps no-op when blocked
    _drain(SubstitutionStep(name="s"), state)
    assert "substitutions" not in state


def test_assemble_renders_via_eraser_tool():
    """When an Eraser MCP tool is in state, assembly calls it to render diagram DSLs (tool use)."""
    state = _seed_state()
    for step in (MigrationReadinessStep(name="r"), SubstitutionStep(name="s"), AdrComplianceStep(name="a")):
        _drain(state and step, state)

    class _FakeEraser:
        def render(self, dsl):
            return types.SimpleNamespace(drawio_xml="<x/>", png_base64="AA")
    state["_eraser_mcp"] = _FakeEraser()
    _drain(AssembleContractStep(name="asm"), state)
    assert all(d.get("drawio_xml") == "<x/>" for d in state["diagrams"])   # tool was called per diagram
