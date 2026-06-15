"""assemble_blueprint — DETERMINISTIC assembly with synchronous Eraser MCP rendering.

Given validated ArchitectureSelections + spec + plan, produces:
  1. app-blueprint.md   (§1-§9 governance — PRIMARY)
  2. app-blueprint.json (DERIVED, schema-conformant)
  3. Eraser DSL constructed from topology, sent to the Eraser MCP server, which renders
     .drawio.xml + .png synchronously (one call per diagram).

The md/json/DSL construction is deterministic and tested. The Eraser MCP transport is the
live seam (inject eraser_mcp in tests). Durable storage of the artifacts (GCS + AlloyDB
pointer) is handled by the server via the BlueprintArtifactStore.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from assembly.derive_json import derive_json
from assembly.render_markdown import render_markdown
from assembly.selections import ArchitectureSelections
from clients.eraser_mcp import EraserMcpClient
from models.blueprint import AppBlueprint
from pipeline.dsl_builder import build_component_dsl, build_hadr_dsl


@dataclass
class AssembledBlueprint:
    markdown: str
    json: dict
    diagrams: list = field(default_factory=list)   # [{name, dsl, drawio_xml, png_base64}]


def _selections_to_appblueprint(sel: ArchitectureSelections, json_doc: dict) -> AppBlueprint:
    return AppBlueprint(**json_doc)


def assemble_blueprint(sel: ArchitectureSelections, spec: str, plan: str,
                       eraser_mcp: EraserMcpClient | None = None) -> AssembledBlueprint:
    """Build md + json, construct the Eraser DSL, and render diagrams synchronously via the
    Eraser MCP server. Returns the full blueprint with rendered .drawio.xml + .png."""
    component_png = "component-topology.png"
    hadr_png = "hadr-lifecycle.png"

    markdown = render_markdown(sel, component_png, hadr_png)
    json_doc = derive_json(sel, spec, plan, markdown)
    bp = _selections_to_appblueprint(sel, json_doc)

    component_dsl = build_component_dsl(bp)
    hadr_dsl = build_hadr_dsl(bp)

    eraser = eraser_mcp or EraserMcpClient()
    diagrams = []
    for name, dsl in [("component-topology", component_dsl), ("hadr-lifecycle", hadr_dsl)]:
        res = eraser.render(dsl)        # synchronous: DSL -> drawio_xml + png_base64
        diagrams.append({"name": name, "dsl": dsl,
                         "drawio_xml": res.drawio_xml, "png_base64": res.png_base64})

    return AssembledBlueprint(markdown=markdown, json=json_doc, diagrams=diagrams)
