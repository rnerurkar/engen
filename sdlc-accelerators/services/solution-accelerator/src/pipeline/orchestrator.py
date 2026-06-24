"""Background pipeline orchestrator for the Solution Accelerator.

Pipeline (from architecture doc, line 211):
  validate_spec -> recommend_architecture (RAG) -> discover_integrations (Apigee API Hub)
  -> adr_compliance_check -> assemble_blueprint -> DSL -> diagrams

IP boundary: NO meta-skills, NO STL, NO signed Design Contracts (those are AgentForge).
This platform uses RAG + skill-constrained generation. The single reasoning stage
(recommend_architecture) is human-authored via the curated system prompt.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from clients.eraser_mcp import EraserMcpClient
from models.blueprint import AppBlueprint
from pipeline.dsl_builder import build_component_dsl, build_hadr_dsl


def run_pipeline(spec: str, plan: str, eraser_mcp=None, model_fn=None) -> dict:
    """Execute the full Solution Accelerator pipeline end to end.

    validate_spec -> retrieve (RAG + API Hub) -> recommend_architecture (the single LlmAgent,
    live Gemini via reasoning.llm_provider) -> parse selections -> validate_composition ->
    assemble_blueprint (deterministic; renders diagrams via the Eraser MCP server).

    The reasoning stage runs the WIRED live path: RecommendArchitecture.run() binds the
    human-authored curated system prompt and calls Gemini. `model_fn` injects a model in tests;
    in production it is None and the live provider is used (configure credentials per
    reasoning/llm_provider.py). If the live path is unconfigured, invoke_llm_agent raises
    NotImplementedError with actionable guidance, which blueprint_start surfaces as task failure.

    Returns {markdown, json, diagrams} for blueprint_start to persist to the artifact store.
    """
    from assembly.validate_composition import validate_composition
    from reasoning.recommend_architecture import RecommendArchitecture

    # Stages 0-3: validate_spec -> retrieve -> the LlmAgent reasons -> parse selections.
    selections = RecommendArchitecture().run(spec, plan, model_fn=model_fn)

    # Stage 4: deterministic composition check (LoopAgent cannot nest in ParallelAgent, etc.).
    comp = validate_composition(_agent_tree_dict(selections.agent_tree))
    if not comp.valid:
        raise ValueError("validate_composition failed: "
                         + "; ".join(v.detail for v in comp.violations))

    # Stages 5-8: deterministic assembly (.md + .json + diagrams via the Eraser MCP server).
    return assemble_from_selections(selections, spec, plan, eraser_mcp=eraser_mcp)


def _agent_tree_dict(node) -> dict:
    """Shape an AgentSelection tree into the dict validate_composition expects."""
    return {
        "type": getattr(node, "type", ""),
        "name": getattr(node, "name", ""),
        "children": [_agent_tree_dict(c) for c in getattr(node, "children", [])],
    }


def run_deterministic_stages(bp: AppBlueprint, eraser_mcp=None) -> dict:
    """Stages 8-11 in isolation: given a complete AppBlueprint, build the DSL and render
    diagrams via the Eraser MCP server (two-phase: submit DSL, then fetch drawio+png).
    DSL construction is deterministic; Eraser MCP transport is the seam (inject in tests).
    """
    eraser = eraser_mcp or EraserMcpClient()
    component_dsl = build_component_dsl(bp)
    hadr_dsl = build_hadr_dsl(bp)
    diagrams = []
    for name, dsl in [("component-topology", component_dsl), ("hadr-lifecycle", hadr_dsl)]:
        res = eraser.render(dsl)
        diagrams.append({"name": name, "dsl": dsl,
                         "drawio_xml": res.drawio_xml, "png_base64": res.png_base64})
    return {
        "diagrams": diagrams,
        "json": bp.model_dump(),
    }


def assemble_from_selections(selections, spec: str, plan: str, eraser_mcp=None) -> dict:
    """The deterministic assembly path (stages 8-11): selections -> .md + .json + diagrams.
    Runs AFTER recommend_architecture produces validated selections.

    Synchronous Eraser MCP rendering: assemble_blueprint() builds md+json+DSL and renders
    each diagram via the Eraser MCP server in one call. The server then persists all artifacts
    to the BlueprintArtifactStore (GCS + AlloyDB pointer) for blueprint_result to read back.
    """
    from assembly.assemble import assemble_blueprint
    result = assemble_blueprint(selections, spec, plan, eraser_mcp=eraser_mcp)
    return {"markdown": result.markdown, "json": result.json, "diagrams": result.diagrams}
