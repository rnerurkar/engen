"""CSA registry loader — parse the upstream `architecture.md` into a component/integration registry.

The CSA Agent (a separate, upstream system — outside this preset's scope) reverse-engineers the legacy
application into a CSA diagram **and** an accompanying `architecture.md`. Both are keyed by stable IDs:
`CSA-COMP-XXX` for components and `INT-XXX` for integrations. This module reads the machine-readable
`architecture.md` (the diagram is the human-facing twin) and builds the current-state registry that
`/accelerator.epic-to-spec` fuses with the Epic's modernization intent.

The architecture.md contract (produced upstream; documented in the developer guide):

    ## Component Inventory
    ### Component: CSA-COMP-001 — Order Service
    - **Technology:** Java 8 / Spring Boot 1.5
    - **Hosting:** on-prem VM (RHEL 7)
    - **Data store:** Oracle 12c
    - **Dependencies:** CSA-COMP-002, CSA-COMP-004

    ## Integration Inventory
    ### Integration: INT-001 — Order Service -> Payment Gateway
    - **Technology + version:** REST/JSON over HTTPS (TLS 1.2)
    - **Integration type:** sync api
    - ... (the eight migration-readiness signals) ...
    - **Components:** CSA-COMP-001, CSA-COMP-003

Deterministic markdown parsing; same architecture.md -> identical registry (and identical hash).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from brownfield.ingest.epic_models import SIGNAL_KEYS

# spec.md label -> ledger signal key (the inverse of SIGNAL_LABEL, case-insensitive).
_LABEL_TO_KEY = {
    "technology + version": "technology",
    "integration type": "type",
    "data flow direction": "direction",
    "criticality": "criticality",
    "coexistence constraint": "coexistence",
    "api surface / contract": "api_surface",
    "state management": "state",
    "data volume + sla": "volume_sla",
}

_COMP_RE = re.compile(
    r"^###\s+Component:\s+(CSA-COMP-\d+)\s+—\s+(.*)$", re.MULTILINE | re.IGNORECASE
)
_INT_RE = re.compile(
    r"^###\s+Integration:\s+(INT-\d+)\s+—\s+(.*)$", re.MULTILINE | re.IGNORECASE
)
_FIELD_RE = re.compile(r"^-\s+\*\*(.+?):\*\*\s+(.*)$", re.MULTILINE)
_COMP_ID = re.compile(r"CSA-COMP-\d+", re.IGNORECASE)
_SUMMARY_RE = re.compile(
    r"^##\s+Application Summary\s*$(.*?)^##\s", re.MULTILINE | re.IGNORECASE | re.DOTALL
)


@dataclass
class CsaComponent:
    component_id: str
    name: str = ""
    attributes: dict[str, str] = field(
        default_factory=dict
    )  # label -> value (verbatim)
    dependencies: list[str] = field(default_factory=list)  # CSA-COMP ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "attributes": self.attributes,
            "dependencies": self.dependencies,
        }


@dataclass
class CsaIntegration:
    int_id: str
    name: str = ""
    signals: dict[str, str] = field(
        default_factory=dict
    )  # signal key -> value (verbatim)
    components: list[str] = field(
        default_factory=list
    )  # CSA-COMP ids this edge connects

    def to_dict(self) -> dict[str, Any]:
        return {
            "int_id": self.int_id,
            "name": self.name,
            "signals": self.signals,
            "components": self.components,
        }


@dataclass
class CsaRegistry:
    app_summary: str = ""
    components: dict[str, CsaComponent] = field(default_factory=dict)
    integrations: list[Any] = field(default_factory=list)  # list[CsaIntegration]
    content_hash: str = ""

    def has(self, component_id: str) -> bool:
        return component_id.upper() in self.components

    def integrations_for(self, component_ids: set[str]) -> list[Any]:
        """Integrations that touch at least one of the given components (stable order by INT id)."""
        wanted = {c.upper() for c in component_ids}
        hits = [
            ig
            for ig in self.integrations
            if wanted.intersection({c.upper() for c in ig.components})
        ]
        return sorted(hits, key=lambda ig: ig.int_id)


def _block(md: str, matches: list[re.Match[str]], i: int) -> str:
    start = matches[i].end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
    return md[start:end]


def load_csa(architecture_md: str) -> CsaRegistry:
    """Parse the CSA architecture.md into a CsaRegistry. Empty/None input yields an empty registry."""
    md = architecture_md or ""
    reg = CsaRegistry()
    reg.content_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()[:12]

    sm = _SUMMARY_RE.search(md + "\n## ")
    if sm:
        reg.app_summary = sm.group(1).strip()

    comp_matches = list(_COMP_RE.finditer(md))
    for i, m in enumerate(comp_matches):
        cid, name = m.group(1).upper(), m.group(2).strip()
        block = _block(md, comp_matches, i)
        attrs: dict[str, str] = {}
        deps: list[str] = []
        for fm in _FIELD_RE.finditer(block):
            label = fm.group(1).strip().lower()
            value = fm.group(2).strip()
            attrs[label] = value
            if label in ("dependencies", "depends on"):
                deps = [d.group(0).upper() for d in _COMP_ID.finditer(value)]
        reg.components[cid] = CsaComponent(
            component_id=cid, name=name, attributes=attrs, dependencies=deps
        )

    int_matches = list(_INT_RE.finditer(md))
    for i, m in enumerate(int_matches):
        iid, name = m.group(1).upper(), m.group(2).strip()
        block = _block(md, int_matches, i)
        signals: dict[str, str] = {}
        comps: list[str] = []
        for fm in _FIELD_RE.finditer(block):
            label = fm.group(1).strip().lower()
            value = fm.group(2).strip()
            key = _LABEL_TO_KEY.get(label)
            if key in SIGNAL_KEYS:
                signals[str(key)] = value
            elif label == "components":
                comps = [c.group(0).upper() for c in _COMP_ID.finditer(value)]
        reg.integrations.append(
            CsaIntegration(int_id=iid, name=name, signals=signals, components=comps)
        )

    reg.integrations.sort(key=lambda ig: ig.int_id)
    return reg
