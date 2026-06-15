"""Reasoning-time assembly: selections -> app-blueprint.md + .json + Eraser DSL.
Validates schema conformance, 9-section round-trip, and determinism.
"""
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/solution-accelerator/src"))
sys.path.insert(0, str(ROOT / "services/governance-guardian/src"))

from assembly.assemble import assemble_blueprint
from clients.eraser_mcp import EraserMcpClient


def _stub_eraser():
    """Deterministic Eraser MCP stand-in: synchronous render -> drawio_xml + png."""
    def _render(dsl):
        return {"drawio_xml": f"<mxGraphModel id='{abs(hash(dsl)) % 10000}'/>",
                "png_base64": "iVBORw0KGgo="}
    return EraserMcpClient(_render=_render)
from assembly.selections import (
    AgentSelection,
    ArchitectureSelections,
    BusinessRuleSelection,
    PatternSelection,
    SkillSelection,
    ToolSelection,
)


def _fnol_selections():
    tree = AgentSelection(name="fnol_coordinator", type="SequentialAgent", role="Orchestrates", children=[
        AgentSelection(name="extract_details", type="LlmAgent", role="Extract", model="gemini-2.0-flash",
                       tools=["claims-db-mcp", "coverage_calculator_fn"]),
        AgentSelection(name="severity_classifier", type="LlmAgent", role="Classify", model="gemini-2.0-flash",
                       tools=["severity_classifier_fn", "body-shop-a2a"]),
    ])
    return ArchitectureSelections(
        solution_id="fnol", use_case="FNOL intake", archetype="agentic", primary_pattern="SequentialAgent",
        pattern_composition=[PatternSelection(pattern="SequentialAgent", role="orchestration", confidence="high")],
        agent_tree=tree,
        tools=[
            ToolSelection(name="claims-db-mcp", type="mcp_server", assigned_to="extract_details", discovered_via="Apigee API Hub"),
            ToolSelection(name="coverage_calculator_fn", type="function_tool", assigned_to="extract_details"),
            ToolSelection(name="severity_classifier_fn", type="function_tool", assigned_to="severity_classifier"),
            ToolSelection(name="body-shop-a2a", type="a2a_agent", assigned_to="severity_classifier", discovered_via="Apigee API Hub"),
        ],
        skills=[SkillSelection(name="adk-agents", sha="abc", version="2.1.0", assigned_to="fnol_coordinator")],
        business_rules=[BusinessRuleSelection(id="BR-001", rule="IF x THEN y", implemented_by="severity_classifier_fn")],
        screening={"model_armor_level": "strict", "agents_with_input_screening": ["extract_details"],
                   "agents_with_output_screening": ["severity_classifier"]},
        agent_identity=[{"agent": "fnol_coordinator", "service_account": "sa@p", "capabilities": ["delegation-only"]}],
        infra_modules=[{"module": "tf-cloud-run-agent", "source": "github.com/c/m", "version": "v2.1.0", "variables": {"region": "us-east1"}}],
        hadr={"strategy": "Warm Standby", "primary_region": "us-east1", "dr_region": "us-central1"},
        nfr_targets={"availability": {"target": "99.9%"}}, observability={"tracing": "Cloud Trace"},
        overall_confidence="high",
    )


def test_assemble_produces_three_artifacts():
    r = assemble_blueprint(_fnol_selections(), "spec", "plan", eraser_mcp=_stub_eraser())
    assert r.markdown.count("## §") == 9
    assert len(r.json) >= 12
    assert {d["name"] for d in r.diagrams} == {"component-topology", "hadr-lifecycle"}


def test_derived_json_validates_schema():
    r = assemble_blueprint(_fnol_selections(), "spec", "plan", eraser_mcp=_stub_eraser())
    schema = json.loads((ROOT / "schemas/app-blueprint.schema.json").read_text())
    jsonschema.validate(r.json, schema)


def test_markdown_roundtrips_nine_sections():
    from extraction.sections import completeness, extract_sections
    r = assemble_blueprint(_fnol_selections(), "spec", "plan", eraser_mcp=_stub_eraser())
    secs = extract_sections(r.markdown)
    assert sorted(secs.keys()) == list(range(1, 10))
    assert completeness(secs) == []


def test_assembly_is_deterministic():
    a = assemble_blueprint(_fnol_selections(), "spec", "plan", eraser_mcp=_stub_eraser())
    b = assemble_blueprint(_fnol_selections(), "spec", "plan", eraser_mcp=_stub_eraser())
    assert a.markdown == b.markdown
    assert a.json == b.json
    assert [d["dsl"] for d in a.diagrams] == [d["dsl"] for d in b.diagrams]


def test_eraser_dsl_present_and_nonempty():
    r = assemble_blueprint(_fnol_selections(), "spec", "plan", eraser_mcp=_stub_eraser())
    for d in r.diagrams:
        assert d["dsl"].strip()
        assert "drawio_xml" in d


def test_synchronous_eraser_mcp_render():
    """assemble_blueprint renders diagrams synchronously via the Eraser MCP server."""
    r = assemble_blueprint(_fnol_selections(), "spec", "plan", eraser_mcp=_stub_eraser())
    assert all(d["drawio_xml"].startswith("<mxGraphModel") for d in r.diagrams)
    assert all(d["png_base64"] for d in r.diagrams)


def test_assemble_without_eraser_mcp_raises_at_seam():
    """No fabrication: without an Eraser MCP client, submit raises rather than faking a render."""
    import pytest
    with pytest.raises(NotImplementedError):
        assemble_blueprint(_fnol_selections(), "spec", "plan")
