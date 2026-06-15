"""Refresh bidirectional sync: Step 0 detect, drawio parse, reconcile, validate, orchestrate.
Deterministic engine fully tested; LLM seams injected as deterministic stand-ins.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/solution-accelerator/src"))

from refresh.detect import Case, detect, write_hashes
from refresh.drawio_parser import parse_drawio
from refresh.orchestrator import refresh
from refresh.reconcile import DeltaKind, reconcile
from refresh.validate_sync import validate_sync

COMPONENT_XML = """<mxGraphModel><root>
  <mxCell id="0"/><mxCell id="1" parent="0"/>
  <mxCell id="n1" value="fnol_coordinator" vertex="1" parent="1"/>
  <mxCell id="n2" value="extract_details" vertex="1" parent="1"/>
  <mxCell id="n3" value="claims-db-mcp" vertex="1" parent="1"/>
  <mxCell id="e1" value="delegates" edge="1" source="n1" target="n2" parent="1"/>
  <mxCell id="e2" value="mcp_server" edge="1" source="n2" target="n3" parent="1"/>
</root></mxGraphModel>"""

LAST_JSON = {
    "metadata": {"solution_id": "fnol", "archetype": "agentic",
                 "source_hashes": {"spec_hash": "sha256:a", "plan_hash": "sha256:b", "blueprint_hash": "sha256:c"}},
    "pattern_composition": {"primary_pattern": "SequentialAgent", "composition": []},
    "adk_agent_tree": {"root": {"name": "fnol_coordinator", "type": "SequentialAgent", "role": "x",
        "children": [{"name": "extract_details", "type": "LlmAgent", "role": "y", "children": []}]}},
    "tool_bindings": [{"name": "claims-db-mcp", "type": "mcp_server", "assigned_to": "extract_details"}],
    "business_rules": [], "agent_identity_config": [],
    "screening_config": {"model_armor_level": "x", "agents_with_input_screening": [], "agents_with_output_screening": []},
    "observability_config": {}, "infra_modules": [], "hadr_config": {}, "nfr_targets": {},
}

MD_9 = "\n".join(f"## §{i}. Section {i}\nbody\n" for i in range(1, 10))


def test_detect_classifies_cases(tmp_path):
    hp = str(tmp_path / ".accelerator-hashes")
    write_hashes(hp, "MD1", {"c.drawio.xml": "X1"}, {"k": "v"})
    assert detect("MD2", {"c.drawio.xml": "X1"}, hp).case == Case.A
    assert detect("MD1", {"c.drawio.xml": "X2"}, hp).case == Case.B
    assert detect("MD2", {"c.drawio.xml": "X2"}, hp).case == Case.C
    assert detect("MD1", {"c.drawio.xml": "X1"}, hp).case == Case.NONE


def test_drawio_parser_extracts_nodes_and_edges():
    t = parse_drawio(COMPONENT_XML)
    assert {"fnol_coordinator", "extract_details", "claims-db-mcp"} <= t.node_labels()
    assert any(e.source_label == "fnol_coordinator" and e.target_label == "extract_details" for e in t.edges)


def test_reconcile_detects_conflict():
    r = reconcile(
        md_agent_names={"fnol_coordinator", "extract_details"},
        drawio_node_labels={"fnol_coordinator", "extract_details"},
        md_tool_assignments={"claims-db-mcp": "extract_details"},
        drawio_tool_assignments={"claims-db-mcp": "fnol_coordinator"},
        last_json=LAST_JSON,
    )
    assert r.needs_developer
    assert r.conflicts[0].kind == DeltaKind.CONFLICT


def test_reconcile_auto_merges_agreement():
    r = reconcile(
        md_agent_names={"fnol_coordinator", "extract_details", "fraud_detector"},
        drawio_node_labels={"fnol_coordinator", "extract_details", "fraud_detector"},
        md_tool_assignments={}, drawio_tool_assignments={}, last_json=LAST_JSON,
    )
    assert not r.needs_developer
    assert any(d.kind == DeltaKind.AGREE and d.entity == "fraud_detector" for d in r.deltas)


def test_validate_sync_parity():
    rep = validate_sync(MD_9, {"fnol_coordinator", "extract_details", "claims-db-mcp"}, LAST_JSON)
    names = {c.name for c in rep.checks}
    assert {"md_completeness", "node_parity", "name_matching", "adjacency", "json_consistency"} == names
    assert rep.passed


def test_refresh_case_none(tmp_path):
    hp = str(tmp_path / ".accelerator-hashes")
    write_hashes(hp, MD_9, {"component.drawio.xml": COMPONENT_XML}, LAST_JSON)
    r = refresh(MD_9, {"component.drawio.xml": COMPONENT_XML}, "spec", "plan", hp, LAST_JSON)
    assert r.sync_report.case == "NONE"


def test_refresh_case_a_with_seams(tmp_path):
    """Case A: only .md changed. Inject LLM + deterministic seams."""
    hp = str(tmp_path / ".accelerator-hashes")
    write_hashes(hp, MD_9, {"component.drawio.xml": COMPONENT_XML}, LAST_JSON)
    edited_md = MD_9 + "\n## §2. Component Topology\nAdded fraud_detector agent.\n"

    def md_to_topology(md, spec, plan):  # LLM seam stand-in
        return {"root": LAST_JSON["adk_agent_tree"]["root"]}
    def derive_json_fn(topology, spec, plan, md):
        return LAST_JSON
    def build_drawio_fn(json_doc):
        return {"component.drawio.xml": COMPONENT_XML}

    r = refresh(edited_md, {"component.drawio.xml": COMPONENT_XML}, "spec", "plan", hp, LAST_JSON,
                md_to_topology=md_to_topology, derive_json_fn=derive_json_fn, build_drawio_fn=build_drawio_fn)
    assert r.sync_report.case == "A"
    assert ".drawio regenerated from .md topology" in r.sync_report.synced
    assert r.structural_report is not None


def test_refresh_case_c_surfaces_conflict(tmp_path):
    """Case C with a genuine conflict must surface it, not resolve silently."""
    hp = str(tmp_path / ".accelerator-hashes")
    write_hashes(hp, MD_9, {"component.drawio.xml": COMPONENT_XML}, LAST_JSON)
    edited_md = MD_9 + "\nedited\n"
    # diagram reassigns claims-db-mcp to fnol_coordinator (conflict vs .md's extract_details)
    conflict_xml = COMPONENT_XML.replace('source="n2" target="n3"', 'source="n1" target="n3"')

    def md_to_topology(md, spec, plan):
        return {"root": LAST_JSON["adk_agent_tree"]["root"],
                "tool_bindings": [{"name": "claims-db-mcp", "assigned_to": "extract_details"}]}

    r = refresh(edited_md, {"component.drawio.xml": conflict_xml}, "spec", "plan", hp, LAST_JSON,
                md_to_topology=md_to_topology)
    assert r.sync_report.case == "C"
    assert r.sync_report.conflicts  # surfaced, not silently resolved
    assert "developer resolution" in r.sync_report.note.lower()


def test_refresh_case_a_missing_seam_raises(tmp_path):
    """No fabrication: Case A without the LLM seam raises rather than guessing."""
    import pytest
    hp = str(tmp_path / ".accelerator-hashes")
    write_hashes(hp, MD_9, {"component.drawio.xml": COMPONENT_XML}, LAST_JSON)
    with pytest.raises(NotImplementedError):
        refresh(MD_9 + "\nedit\n", {"component.drawio.xml": COMPONENT_XML}, "spec", "plan", hp, LAST_JSON)
