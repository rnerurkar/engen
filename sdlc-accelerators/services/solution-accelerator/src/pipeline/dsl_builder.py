"""Stage 8: deterministic Eraser.io DSL construction from the agent topology.
No LLM. Same blueprint in -> byte-identical DSL out (sorted, stable ordering).
Validated against examples/fnol/diagrams/fnol-eraser-dsl-examples.md.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models.blueprint import AgentNode, AppBlueprint


def _walk(node: AgentNode):
    yield node
    for child in node.children:
        yield from _walk(child)


def build_component_dsl(bp: AppBlueprint) -> str:
    """Serialize the component topology to Eraser.io DSL."""
    lines: list[str] = ["// Component Topology", "// Generated deterministically by Solution Accelerator", ""]

    # Nodes — agents, sorted by name for determinism
    agents = sorted(_walk(bp.adk_agent_tree.root), key=lambda a: a.name)
    for a in agents:
        icon = {"SequentialAgent": "workflow", "ParallelAgent": "split",
                "LlmAgent": "robot", "LoopAgent": "refresh", "CustomAgent": "user"}.get(a.type, "box")
        lines.append(f'{a.name} [icon: {icon}] {{')
        lines.append(f'  label: "{a.name}"')
        lines.append(f'  type: "{a.type}"')
        if a.model:
            lines.append(f'  model: "{a.model}"')
        lines.append("}")

    # Tool nodes, sorted
    for tb in sorted(bp.tool_bindings, key=lambda t: t.name):
        icon = {"mcp_server": "database", "a2a_agent": "building", "function_tool": "code"}.get(tb.type, "box")
        lines.append(f'{tb.name.replace("-", "_")} [icon: {icon}] {{ label: "{tb.name}" type: "{tb.type}" }}')

    # Hierarchy edges (parent > child)
    for a in agents:
        for child in a.children:
            lines.append(f'{a.name} > {child.name}: "delegates"')

    # Tool binding edges, sorted
    for tb in sorted(bp.tool_bindings, key=lambda t: (t.assigned_to, t.name)):
        lines.append(f'{tb.assigned_to} > {tb.name.replace("-", "_")}: "{tb.type}"')

    return "\n".join(lines) + "\n"


def build_hadr_dsl(bp: AppBlueprint) -> str:
    """Serialize the HA/DR lifecycle to Eraser.io DSL from hadr_config."""
    cfg = bp.hadr_config
    lines = ["// HA/DR Lifecycle", f'// Strategy: {cfg.get("strategy", "unknown")}', ""]
    primary = cfg.get("primary_region", "primary")
    dr = cfg.get("dr_region", "dr")
    lines.append(f'{primary.replace("-", "_")} [icon: region] {{ label: "{primary} (Primary)" }}')
    lines.append(f'{dr.replace("-", "_")} [icon: region] {{ label: "{dr} (DR)" }}')
    lines.append(f'{primary.replace("-", "_")} > {dr.replace("-", "_")}: "replication"')
    return "\n".join(lines) + "\n"
