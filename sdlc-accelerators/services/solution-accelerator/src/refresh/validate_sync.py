"""Refresh Step 2 — VALIDATE post-sync consistency (architecture lines 1151-1157).
All deterministic. Returns a structural_report (PASS/WARN per check).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dataclasses import dataclass, field

from extraction_compat import extract_sections_compat  # local shim below


@dataclass
class Check:
    name: str
    status: str   # PASS | WARN
    detail: str = ""


@dataclass
class StructuralReport:
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.status == "PASS" for c in self.checks)


def validate_sync(blueprint_md: str, drawio_node_labels: set[str], json_doc: dict) -> StructuralReport:
    rep = StructuralReport()

    # 1. .md completeness: all 9 sections present
    secs = extract_sections_compat(blueprint_md)
    missing = [n for n in range(1, 10) if n not in secs]
    rep.checks.append(Check("md_completeness", "PASS" if not missing else "WARN",
                            "all 9 sections" if not missing else f"missing {missing}"))

    # agent names from json
    def agent_names(n):
        names = {n["name"]}
        for c in n.get("children", []):
            names |= agent_names(c)
        return names
    json_agents = agent_names(json_doc["adk_agent_tree"]["root"])

    # 2. node parity: agent count matches between json and diagram (diagram includes tool nodes too)
    diagram_agents = drawio_node_labels & json_agents
    rep.checks.append(Check("node_parity", "PASS" if json_agents <= drawio_node_labels else "WARN",
                            f"{len(diagram_agents)}/{len(json_agents)} agents in diagram"))

    # 3. name matching: every json agent appears in the diagram
    missing_in_diagram = json_agents - drawio_node_labels
    rep.checks.append(Check("name_matching", "PASS" if not missing_in_diagram else "WARN",
                            ("all agent names match" if not missing_in_diagram
                             else f"not in diagram: {missing_in_diagram}")))

    # 4. adjacency: LoopAgent cannot nest directly inside ParallelAgent
    rep.checks.append(_adjacency_check(json_doc))

    # 5. json consistency: tool bindings reference existing agents
    bad = [t["name"] for t in json_doc.get("tool_bindings", []) if t["assigned_to"] not in json_agents]
    rep.checks.append(Check("json_consistency", "PASS" if not bad else "WARN",
                            "tool bindings valid" if not bad else f"orphan bindings: {bad}"))
    return rep


def _adjacency_check(json_doc: dict) -> Check:
    bad = []
    def walk(n, parent_type=None):
        if n["type"] == "LoopAgent" and parent_type == "ParallelAgent":
            bad.append(n["name"])
        for c in n.get("children", []):
            walk(c, n["type"])
    walk(json_doc["adk_agent_tree"]["root"])
    return Check("adjacency", "PASS" if not bad else "WARN",
                 "adjacency valid" if not bad else f"LoopAgent in ParallelAgent: {bad}")
