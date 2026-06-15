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
from reasoning.recommend_architecture import RecommendArchitecture


def run_pipeline(spec: str, plan: str, eraser_mcp=None) -> dict:
    """Execute the Solution Accelerator pipeline.

    The recommend_architecture stage requires the human-authored curated system prompt;
    until wired it raises NotImplementedError (surfaced by blueprint_start). Stages 8-11
    (DSL + assemble, diagrams via the Eraser MCP server) are deterministic and fully
    implemented (see run_deterministic_stages / assemble_from_selections).
    """
    # Stage 0: validate_spec would run here (quality gate).
    signals = {"ordering_words": [], "data_systems": []}

    # Stage 1: recommend_architecture — single RAG-grounded reasoning stage (HUMAN-AUTHORED)
    ra = RecommendArchitecture()
    retrieved = ra.retrieve(signals)
    ra.reason(spec, plan, retrieved)  # raises until the curated prompt is wired

    # Stage 2: discover_integrations (deterministic) — not reached until stage 1 authored.
    raise NotImplementedError(
        "Pipeline reaches assemble once recommend_architecture's curated prompt is wired."
    )


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
