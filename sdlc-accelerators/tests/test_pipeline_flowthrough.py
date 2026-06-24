"""run_pipeline end-to-end flow-through (the wired reasoning seam).

Proves blueprint_start's pipeline now reaches assembly: validate -> retrieve -> the LlmAgent
(injected here) -> parse -> validate_composition -> assemble. The live Gemini call is exercised
via an injected model_fn (no credentials in CI); production passes model_fn=None and uses the
live provider. Also proves the live path raises a clear, actionable error when unconfigured."""
from pathlib import Path

from clients.eraser_mcp import EraserMcpClient
from pipeline.orchestrator import run_pipeline

ROOT = Path(__file__).resolve().parents[1]
SPEC = (ROOT / "examples/fnol/inputs/spec.md").read_text()
PLAN = (ROOT / "examples/fnol/inputs/plan.md").read_text()

# Reuse the same model output shape the recommend test uses (simulates the live Gemini JSON).
from test_recommend_architecture import _stub_model  # noqa: E402


def _eraser():
    return EraserMcpClient(_render=lambda dsl: {"drawio_xml": "<mxGraphModel/>", "png_base64": "AA"})


def test_pipeline_flows_through_to_assembly():
    out = run_pipeline(SPEC, PLAN, eraser_mcp=_eraser(), model_fn=_stub_model)
    # reaches assembly: markdown + json + diagrams (previously raised NotImplementedError here)
    assert out["markdown"].lstrip().startswith("#")
    assert out["json"]["metadata"]["solution_id"] == "fnol"
    assert len(out["diagrams"]) >= 1
    assert out["diagrams"][0]["drawio_xml"] == "<mxGraphModel/>"


def test_pipeline_runs_composition_check():
    # The stub's agent_tree is valid (SequentialAgent root) → no composition error.
    out = run_pipeline(SPEC, PLAN, eraser_mcp=_eraser(), model_fn=_stub_model)
    assert out["json"]["adk_agent_tree"]["root"]["type"] == "SequentialAgent"


def test_live_path_unconfigured_raises_actionable_error(monkeypatch):
    """With no model_fn and no credentials, the wired live path raises a clear error
    (not a silent stub). blueprint_start surfaces this as task failure."""
    import reasoning.llm_provider as prov
    monkeypatch.setattr(prov, "available", lambda: (False, "no credentials (test)"))
    import pytest
    with pytest.raises((NotImplementedError, RuntimeError)) as ei:
        run_pipeline(SPEC, PLAN, eraser_mcp=_eraser(), model_fn=None)
    assert "not" in str(ei.value).lower() or "credential" in str(ei.value).lower()
