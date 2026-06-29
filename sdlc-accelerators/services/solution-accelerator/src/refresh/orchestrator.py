"""refresh() — the bidirectional sync orchestrator (architecture lines 1100-1163).

Steps: 0 DETECT -> 1 SYNC (case A/B/C) -> 2 VALIDATE -> 3 REGENERATE.

Deterministic parts (detect, drawio parse, reconcile-diff, validate, json/hash regen) are
real and tested. The two prose<->structure bridges are LLM seams, injected as callables:
  - md_to_topology(md, spec, plan) -> agent topology    (Case A, C: prose -> structure)
  - topology_to_md(json_doc, current_md) -> updated md   (Case B, C: structure -> prose)
Tests inject deterministic stand-ins; production wires the Solution Accelerator LLM harness.

Per ARB M-1: spec/plan are read from the workspace, not passed by the developer.
Per ARB M-2: the package is §1-§9 (not the old §1-§7 + §8-§12 model).
"""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from collections.abc import Callable
from dataclasses import dataclass, field

from refresh.detect import Case, detect, write_hashes
from refresh.drawio_parser import parse_drawio
from refresh.reconcile import Reconciliation, reconcile
from refresh.validate_sync import StructuralReport, validate_sync


@dataclass
class SyncReport:
    case: str
    changed: list[str] = field(default_factory=list)
    synced: list[str] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    note: str = ""


@dataclass
class RefreshResult:
    sync_report: SyncReport
    structural_report: StructuralReport | None
    updated_md: str | None = None
    updated_drawio: dict[str, Any] = field(default_factory=dict)
    updated_json: dict[str, Any] | None = None


# LLM seam types
MdToTopology = Callable[
    [str, str, str], dict[str, Any]
]  # (md, spec, plan) -> agent topology dict
TopologyToMd = Callable[
    [dict[str, Any], str], str
]  # (json_doc, current_md) -> updated md


def refresh(
    blueprint_md: str,
    drawio_files: dict[str, Any],
    spec: str,
    plan: str,
    hashes_path: str,
    last_json: dict[str, Any],
    md_to_topology: MdToTopology | None = None,
    topology_to_md: TopologyToMd | None = None,
    derive_json_fn: Callable[..., Any] | None = None,
    build_drawio_fn: Callable[..., Any] | None = None,
    resolve_conflict_fn: Callable[[Reconciliation], dict[str, Any]] | None = None,
) -> RefreshResult:
    """Orchestrate bidirectional sync. LLM-dependent steps require the injected callables;
    if a needed seam is missing for the detected case, raises NotImplementedError (no fabrication)."""

    # Step 0: DETECT
    det = detect(blueprint_md, drawio_files, hashes_path)
    sync = SyncReport(case=det.case.value)
    if det.md_changed:
        sync.changed.append(".md")
    if det.drawio_changed:
        sync.changed.append(".drawio")

    if det.case == Case.NONE:
        sync.note = "No changes detected."
        return RefreshResult(sync_report=sync, structural_report=None)

    updated_md = blueprint_md
    updated_drawio = dict(drawio_files)
    json_doc = dict(last_json)

    # Step 1: SYNC
    if det.case == Case.A:
        # prose -> topology (LLM), then regenerate json + drawio deterministically
        if md_to_topology is None or derive_json_fn is None or build_drawio_fn is None:
            raise NotImplementedError(
                "Case A needs md_to_topology (LLM seam) + derive_json + build_drawio."
            )
        topology = md_to_topology(blueprint_md, spec, plan)
        json_doc = derive_json_fn(topology, spec, plan, blueprint_md)
        updated_drawio = build_drawio_fn(json_doc)
        sync.synced.append(".drawio regenerated from .md topology")

    elif det.case == Case.B:
        # drawio -> topology (deterministic parse) -> update json -> prose (LLM)
        if topology_to_md is None or derive_json_fn is None:
            raise NotImplementedError(
                "Case B needs topology_to_md (LLM seam) + derive_json."
            )
        # parse diagram, update json topology to match (handled by derive via topology), then prose
        json_doc = derive_json_fn(
            _drawio_to_topology(drawio_files), spec, plan, blueprint_md
        )
        updated_md = topology_to_md(json_doc, blueprint_md)
        sync.synced.append(".md §2 narrative updated from diagram")

    elif det.case == Case.C:
        # reconcile both against last-known json
        if md_to_topology is None:
            raise NotImplementedError(
                "Case C needs md_to_topology (LLM seam) to extract .md topology."
            )
        md_topo = md_to_topology(blueprint_md, spec, plan)
        recon = reconcile(
            md_agent_names=_names(md_topo),
            drawio_node_labels=_labels(drawio_files),
            md_tool_assignments=_tools(md_topo),
            drawio_tool_assignments=_drawio_tools(drawio_files),
            last_json=last_json,
        )
        if recon.needs_developer:
            if resolve_conflict_fn is None:
                # Surface conflicts — do NOT silently resolve (human in control)
                sync.conflicts = [
                    {
                        "entity": d.entity,
                        "md": d.md_value,
                        "drawio": d.drawio_value,
                        "detail": d.detail,
                    }
                    for d in recon.conflicts
                ]
                sync.note = "Conflicts require developer resolution."
                return RefreshResult(sync_report=sync, structural_report=None)
            resolution = resolve_conflict_fn(recon)
            md_topo.update(resolution)
        if derive_json_fn is None or build_drawio_fn is None or topology_to_md is None:
            raise NotImplementedError(
                "Case C merge needs derive_json + build_drawio + topology_to_md."
            )
        json_doc = derive_json_fn(md_topo, spec, plan, blueprint_md)
        updated_md = topology_to_md(json_doc, blueprint_md)
        updated_drawio = build_drawio_fn(json_doc)
        sync.synced += [".md reconciled", ".drawio reconciled"]

    # Step 2: VALIDATE
    structural = validate_sync(updated_md, _labels(updated_drawio), json_doc)

    # Step 3: REGENERATE (.json already derived above; update hashes)
    write_hashes(hashes_path, updated_md, updated_drawio, json_doc)

    return RefreshResult(
        sync_report=sync,
        structural_report=structural,
        updated_md=updated_md,
        updated_drawio=updated_drawio,
        updated_json=json_doc,
    )


# --- helpers ---
def _drawio_to_topology(drawio_files: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal topology dict from the (first) component diagram for derive."""
    for name, xml in drawio_files.items():
        if "component" in name:
            t = parse_drawio(xml)
            return {
                "_diagram_nodes": [n.label for n in t.nodes],
                "_diagram_edges": [(e.source_label, e.target_label) for e in t.edges],
            }
    return {}


def _labels(drawio_files: dict[str, Any]) -> set[Any]:
    labels = set()
    for xml in drawio_files.values():
        for n in parse_drawio(xml).nodes:
            labels.add(n.label)
    return labels


def _names(topology: dict[str, Any]) -> set[Any]:
    """Agent names from an md-extracted topology (shape: {root: {...}} or selections-like)."""
    names = set()
    root = topology.get("root") or topology.get("adk_agent_tree", {}).get("root")
    if root:

        def walk(n: Any) -> None:
            names.add(n["name"])
            for c in n.get("children", []):
                walk(c)

        walk(root)
    return names


def _tools(topology: dict[str, Any]) -> dict[str, Any]:
    return {t["name"]: t["assigned_to"] for t in topology.get("tool_bindings", [])}


def _drawio_tools(drawio_files: dict[str, Any]) -> dict[str, Any]:
    """Infer tool->agent assignments from diagram edges labelled with a tool type."""
    assignments = {}
    for xml in drawio_files.values():
        t = parse_drawio(xml)
        for e in t.edges:
            if e.edge_label in ("mcp_server", "a2a_agent", "function_tool"):
                assignments[e.target_label] = e.source_label
    return assignments
