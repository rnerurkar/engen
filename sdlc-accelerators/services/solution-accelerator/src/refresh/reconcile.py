"""Refresh Step 1 (Case C) — reconcile .md topology vs .drawio topology vs last-known .json.

Classifies each delta as AGREE / MD_ONLY / DRAWIO_ONLY / CONFLICT (per architecture lines
1131-1149). AGREE/MD_ONLY/DRAWIO_ONLY auto-merge; CONFLICT is surfaced to the developer,
never silently resolved ("human is always in control").

Topology extraction from .md prose is the LLM seam (md_topology supplied by the harness);
this module does the deterministic DIFF once both topologies are structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeltaKind(str, Enum):
    AGREE = "AGREE"
    MD_ONLY = "MD_ONLY"
    DRAWIO_ONLY = "DRAWIO_ONLY"
    CONFLICT = "CONFLICT"


@dataclass
class Delta:
    kind: DeltaKind
    entity: str
    md_value: str = ""
    drawio_value: str = ""
    detail: str = ""


@dataclass
class Reconciliation:
    deltas: list[Delta] = field(default_factory=list)

    @property
    def conflicts(self) -> list[Delta]:
        return [d for d in self.deltas if d.kind == DeltaKind.CONFLICT]

    @property
    def auto_mergeable(self) -> list[Delta]:
        return [d for d in self.deltas if d.kind != DeltaKind.CONFLICT]

    @property
    def needs_developer(self) -> bool:
        return bool(self.conflicts)


def _agent_names(json_doc: dict[str, Any]) -> set[str]:
    names = set()

    def walk(n: Any) -> None:
        names.add(n["name"])
        for c in n.get("children", []):
            walk(c)

    walk(json_doc["adk_agent_tree"]["root"])
    return names


def _tool_assignments(json_doc: dict[str, Any]) -> dict[str, str]:
    """tool_name -> assigned_to, from last-known json."""
    return {t["name"]: t["assigned_to"] for t in json_doc.get("tool_bindings", [])}


def reconcile(
    md_agent_names: set[str],
    drawio_node_labels: set[str],
    md_tool_assignments: dict[str, str],
    drawio_tool_assignments: dict[str, str],
    last_json: dict[str, Any],
) -> Reconciliation:
    """Diff md vs drawio vs last-known json. Returns classified deltas."""
    recon = Reconciliation()
    last_agents = _agent_names(last_json)

    # Agent additions
    md_added = md_agent_names - last_agents
    drawio_added = drawio_node_labels - last_agents
    for agent in md_added & drawio_added:  # both added same agent
        recon.deltas.append(
            Delta(DeltaKind.AGREE, agent, detail=f"both added agent '{agent}'")
        )
    for agent in md_added - drawio_added:  # only .md added
        recon.deltas.append(
            Delta(
                DeltaKind.MD_ONLY,
                agent,
                md_value="added",
                detail=f".md added '{agent}'",
            )
        )
    for agent in drawio_added - md_added:  # only diagram added
        recon.deltas.append(
            Delta(
                DeltaKind.DRAWIO_ONLY,
                agent,
                drawio_value="added",
                detail=f"diagram added '{agent}'",
            )
        )

    # Tool-assignment conflicts: same tool assigned to different agents in md vs drawio
    for tool in set(md_tool_assignments) | set(drawio_tool_assignments):
        md_to = md_tool_assignments.get(tool)
        dr_to = drawio_tool_assignments.get(tool)
        if md_to and dr_to and md_to != dr_to:
            recon.deltas.append(
                Delta(
                    DeltaKind.CONFLICT,
                    tool,
                    md_value=md_to,
                    drawio_value=dr_to,
                    detail=f".md says {tool}->{md_to}, diagram says {tool}->{dr_to}",
                )
            )
    return recon
