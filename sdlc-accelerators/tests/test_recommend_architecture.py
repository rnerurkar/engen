"""recommend_architecture: signal extraction, validation gate, LLM harness, full pipeline.
Spec/plan stay as markdown throughout (never JSON)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from assembly.assemble import assemble_blueprint
from clients.eraser_mcp import EraserMcpClient
from reasoning.llm_harness import RetrievedContext, build_user_message, load_system_prompt
from reasoning.recommend_architecture import RecommendArchitecture, SpecBlockedError
from reasoning.validate_spec import extract_signals, validate_spec

SPEC = (ROOT / "examples/fnol/inputs/spec.md").read_text()
PLAN = (ROOT / "examples/fnol/inputs/plan.md").read_text()


def _stub_model(system_prompt, user_message):
    assert "You are the Solution Accelerator" in system_prompt
    assert "## spec.md" in user_message  # markdown, not JSON
    return {
        "solution_id": "fnol", "use_case": "FNOL intake", "archetype": "agentic",
        "primary_pattern": "SequentialAgent",
        "pattern_composition": [{"pattern": "SequentialAgent", "role": "orchestration", "confidence": "high"}],
        "agent_tree": {"name": "fnol_coordinator", "type": "SequentialAgent", "role": "Orchestrates",
            "children": [
                {"name": "extract_details", "type": "LlmAgent", "role": "Extract", "model": "gemini-2.0-flash",
                 "tools": ["claims-db-mcp", "coverage_calculator_fn"]},
                {"name": "severity_classifier", "type": "LlmAgent", "role": "Classify", "model": "gemini-2.0-flash",
                 "tools": ["severity_classifier_fn", "body-shop-a2a"]},
            ]},
        "tools": [
            {"name": "claims-db-mcp", "type": "mcp_server", "assigned_to": "extract_details", "discovered_via": "Apigee API Hub", "confidence": 0.95},
            {"name": "coverage_calculator_fn", "type": "function_tool", "assigned_to": "extract_details"},
            {"name": "severity_classifier_fn", "type": "function_tool", "assigned_to": "severity_classifier"},
            {"name": "body-shop-a2a", "type": "a2a_agent", "assigned_to": "severity_classifier", "discovered_via": "Apigee API Hub", "confidence": 0.9},
        ],
        "skills": [{"name": "adk-agents", "sha": "abc", "version": "2.1.0", "assigned_to": "fnol_coordinator"}],
        "business_rules": [{"id": "BR-001", "rule": "IF x THEN y", "implemented_by": "severity_classifier_fn"}],
        "screening": {"model_armor_level": "strict", "agents_with_input_screening": ["extract_details"], "agents_with_output_screening": ["severity_classifier"]},
        "agent_identity": [{"agent": "fnol_coordinator", "service_account": "sa@p", "capabilities": ["delegation-only"]}],
        "infra_modules": [{"module": "tf-cloud-run-agent", "source": "github.com/c/m", "version": "v2.1.0", "variables": {"region": "us-east1"}}],
        "hadr": {"strategy": "Warm Standby", "primary_region": "us-east1", "dr_region": "us-central1"},
        "nfr_targets": {"availability": {"target": "99.9%"}},
        "observability": {"tracing": "Cloud Trace"}, "overall_confidence": "high",
    }


def test_signal_extraction_finds_ordering_words():
    sig = extract_signals(SPEC)
    assert "first" in sig.ordering_words and "in parallel" in sig.ordering_words
    assert len(sig.ordering_words) >= 3


def test_validate_spec_passes_fnol():
    v = validate_spec(SPEC)
    assert not v.blocked
    assert v.quality_score >= 70


def test_validate_spec_blocks_missing_ordering_words():
    bad = "# Spec\n## §2 Workflow\nThe system does stuff.\n## §10 Acceptance Criteria\nGood.\n"
    v = validate_spec(bad)
    assert v.blocked


def test_harness_loads_authored_prompt_and_keeps_markdown():
    p = load_system_prompt()
    assert "You are the Solution Accelerator" in p
    ctx = RetrievedContext(patterns=[], skills=[], integrations=[])
    msg = build_user_message("# spec", "# plan", {"ordering_words": []}, ctx)
    assert "## spec.md" in msg and "## plan.md" in msg


def test_full_pipeline_spec_to_selections():
    sel = RecommendArchitecture().run(SPEC, PLAN, model_fn=_stub_model)
    assert sel.primary_pattern == "SequentialAgent"
    assert sel.agent_tree.name == "fnol_coordinator"
    assert {t.name for t in sel.tools} == {"claims-db-mcp", "coverage_calculator_fn", "severity_classifier_fn", "body-shop-a2a"}


def test_full_pipeline_spec_to_artifacts():
    sel = RecommendArchitecture().run(SPEC, PLAN, model_fn=_stub_model)
    eraser = EraserMcpClient(_render=lambda dsl: {"drawio_xml": "<mxGraphModel/>", "png_base64": "x"})
    result = assemble_blueprint(sel, SPEC, PLAN, eraser_mcp=eraser)
    assert result.markdown.count("## §") == 9
    assert {d["name"] for d in result.diagrams} == {"component-topology", "hadr-lifecycle"}


def test_blocked_spec_raises_with_guidance():
    import pytest
    bad = "# Spec\n## §2 Workflow\nstuff\n## §10 Acceptance Criteria\ngood\n"
    with pytest.raises(SpecBlockedError) as exc:
        RecommendArchitecture().run(bad, "# plan", model_fn=_stub_model)
    assert "ordering words" in str(exc.value)
