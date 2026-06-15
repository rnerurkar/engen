"""Parse .drawio.xml -> topology (nodes, edges). The deterministic inverse of dsl_builder.

Draw.io stores diagrams as mxGraphModel XML: mxCell elements with vertex="1" are nodes
(value=label), edge="1" are edges (source/target reference node ids). This parser extracts
the agent/tool nodes and the delegation/binding edges so Case B/C can diff against .json.

SCOPE: handles the structure our Eraser.io export produces + standard Draw.io shapes.
Arbitrary hand-drawn diagrams with exotic shapes may need richer parsing — flagged, not faked.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field


@dataclass
class DiagramNode:
    node_id: str
    label: str
    node_type: str = ""   # inferred: agent type or tool type if encoded in style/value


@dataclass
class DiagramEdge:
    source_label: str
    target_label: str
    edge_label: str = ""


@dataclass
class DiagramTopology:
    nodes: list[DiagramNode] = field(default_factory=list)
    edges: list[DiagramEdge] = field(default_factory=list)

    def node_labels(self) -> set[str]:
        return {n.label for n in self.nodes}


def _clean_label(value: str) -> str:
    """Draw.io labels can carry HTML; strip tags and whitespace."""
    import re
    text = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(text.split()).strip()


def parse_drawio(xml_content: str) -> DiagramTopology:
    """Extract nodes and edges from a Draw.io mxGraphModel XML string."""
    topo = DiagramTopology()
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return topo  # empty topology on unparseable input; caller treats as no-op/flag

    # mxCell elements may be nested under <root>; find all regardless of depth
    cells = root.iter("mxCell")
    id_to_label: dict[str, str] = {}
    edges_raw = []
    for cell in cells:
        cid = cell.get("id", "")
        value = _clean_label(cell.get("value", ""))
        if cell.get("vertex") == "1":
            id_to_label[cid] = value
            topo.nodes.append(DiagramNode(node_id=cid, label=value))
        elif cell.get("edge") == "1":
            edges_raw.append((cell.get("source", ""), cell.get("target", ""), value))

    for src, tgt, lbl in edges_raw:
        topo.edges.append(DiagramEdge(
            source_label=id_to_label.get(src, src),
            target_label=id_to_label.get(tgt, tgt),
            edge_label=lbl,
        ))
    return topo
