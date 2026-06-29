"""Phase 2: models load FNOL; deterministic stages run and are byte-stable."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from models.blueprint import AppBlueprint
from pipeline.dsl_builder import build_component_dsl
from pipeline.orchestrator import run_deterministic_stages


def _bp():
    return AppBlueprint(**json.loads((ROOT / "examples/fnol/outputs/app-blueprint.json").read_text()))


def test_fnol_loads_through_models():
    bp = _bp()
    assert bp.adk_agent_tree.root.name == "fnol_coordinator"
    assert len(bp.tool_bindings) == 8


def test_component_dsl_is_deterministic():
    bp = _bp()
    assert build_component_dsl(bp) == build_component_dsl(bp)


def test_deterministic_stages_produce_two_diagrams():
    from clients.eraser_mcp import EraserMcpClient
    eraser = EraserMcpClient(_render=lambda dsl: {"drawio_xml": "<mxGraphModel/>", "png_base64": "x"})
    out = run_deterministic_stages(_bp(), eraser_mcp=eraser)
    assert len(out["diagrams"]) == 2
    assert {d["name"] for d in out["diagrams"]} == {"component-topology", "hadr-lifecycle"}
    assert all(d["drawio_xml"] for d in out["diagrams"])  # rendered via Eraser MCP


def test_reasoning_boundary_is_enforced():
    """The reasoning pipeline is now implemented EXCEPT the live model call.
    Without an injected model_fn, run() must raise NotImplementedError at the single
    live seam (the Gemini call) — it must NOT fabricate a model output.
    (SDLC Accelerators uses RAG + skill-constrained generation, not meta-skills —
    those are out-of-scope external IP IP with zero overlap here.)"""
    import pytest
    from reasoning.recommend_architecture import RecommendArchitecture
    ra = RecommendArchitecture()
    # A spec that passes validate_spec so we reach the model seam.
    spec = ("# Spec\n## §2 Workflow\nFirst the system reads, then it classifies, "
            "in parallel it enriches.\n## §5 External Partners\nPartner operates their own system.\n"
            "## §10 Acceptance Criteria\n< 5 min, > 95% accuracy, < 30 sec latency.\n")
    with pytest.raises(NotImplementedError):
        ra.run(spec, "# plan")  # no model_fn -> live Gemini seam raises
