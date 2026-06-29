"""Brownfield Epic-to-Spec data models.

The brownfield archetype begins AFTER an upstream CSA Agent (separate system, outside this preset)
reverse-engineers the legacy application into a **CSA diagram + `architecture.md`**, both keyed by
stable component IDs (`CSA-COMP-XXX`, `INT-XXX`). A Business Analyst / Solution Architect then authors
a Rally Epic from the standard template whose **Modernization Scope** table declares, per CSA component,
a disposition (`Refactor` | `Rehost`) and an AWS target. `/accelerator.epic-to-spec` fuses the two:
Epic intent x CSA ground truth -> a canonical `spec.md`.

Two model families live here:
  * Epic intent — `ScopeItem` (component_id, disposition, aws_target, rationale) parsed from the Epic's
    Modernization Scope table; plus narrative fields (summary, NFRs, acceptance criteria).
  * Epic Signal Ledger (integration-keyed, 8 migration-readiness signals) — retained for the optional
    span-grounded LLM enrichment pass and for back-compat with the readiness gate.

Extractive + span-grounded (where the LLM enrichment runs): every signal carries a verbatim `epic_span`
and a value grounded in that span; a deterministic validator drops the rest. The Modernization Scope
table is parsed deterministically (it is a decision, not a claim) and validated by cross-walk against
the CSA registry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

LEDGER_SCHEMA = "brownfield-epic-signal-ledger/v1"
SCOPE_SCHEMA = "brownfield-modernization-scope-ledger/v1"

# The eight migration-readiness signal fields per integration (keys -> spec.md labels).
SIGNAL_KEYS = [
    "technology",
    "type",
    "direction",
    "criticality",
    "coexistence",
    "api_surface",
    "state",
    "volume_sla",
]
SIGNAL_LABEL = {
    "technology": "Technology + version",
    "type": "Integration type",
    "direction": "Data flow direction",
    "criticality": "Criticality",
    "coexistence": "Coexistence constraint",
    "api_surface": "API surface / contract",
    "state": "State management",
    "volume_sla": "Data volume + SLA",
}
EXPECTED_SLOTS = len(SIGNAL_KEYS)  # 8

# Modernization dispositions in scope for this preset (a subset of the migration "6 R's").
REFACTOR = "Refactor"
REHOST = "Rehost"
DISPOSITIONS = (REFACTOR, REHOST)


def normalize_disposition(raw: str) -> str | None:
    """Map a free-text disposition onto the canonical {Refactor, Rehost}; None if unrecognized."""
    t = (raw or "").strip().lower()
    if t in ("refactor", "re-factor", "re-architect", "rearchitect", "rf"):
        return REFACTOR
    if t in ("rehost", "re-host", "lift-and-shift", "lift and shift", "rh"):
        return REHOST
    return None


@dataclass
class ScopeItem:
    """One row of the Epic's Modernization Scope table: a CSA component and its intended disposition."""

    component_id: str
    disposition: str | None = None  # canonical Refactor|Rehost, or None if invalid
    aws_target: str = ""
    rationale: str = ""
    raw_disposition: str = ""

    @property
    def valid_disposition(self) -> bool:
        return self.disposition in DISPOSITIONS

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "disposition": self.disposition,
            "aws_target": self.aws_target,
            "rationale": self.rationale,
        }


# Markdown table row: | CSA-COMP-001 | Refactor | ECS Fargate + Aurora | break monolith |
_SCOPE_ROW = re.compile(r"^\s*\|(?P<cells>.+)\|\s*$")
_COMP_ID = re.compile(r"CSA-COMP-\d+", re.IGNORECASE)


def parse_scope_table(text: str) -> list[ScopeItem]:
    """Parse the Modernization Scope markdown table from the Epic body. Tolerant of header/divider
    rows and column order; a row is in scope only if its first cell contains a CSA-COMP id."""
    items: list[ScopeItem] = []
    seen: set[str] = set()
    for line in (text or "").splitlines():
        m = _SCOPE_ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group("cells").split("|")]
        if not cells or not _COMP_ID.search(cells[0] or ""):
            continue  # header, divider, or non-component row
        cid_match = _COMP_ID.search(cells[0])
        if cid_match is None:
            continue
        cid = cid_match.group(0).upper()
        if cid in seen:
            continue
        seen.add(cid)
        raw_disp = cells[1] if len(cells) > 1 else ""
        items.append(
            ScopeItem(
                component_id=cid,
                disposition=normalize_disposition(raw_disp),
                raw_disposition=raw_disp,
                aws_target=cells[2] if len(cells) > 2 else "",
                rationale=cells[3] if len(cells) > 3 else "",
            )
        )
    return items


@dataclass
class EpicProvenance:
    formatted_id: str = ""
    object_version: int | None = None
    last_update_date: str = ""
    source: str = "rally"
    csa_hash: str = ""  # short sha256 of the CSA architecture.md (drift detection for the CSA source)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "formatted_id": self.formatted_id,
            "object_version": self.object_version,
            "last_update_date": self.last_update_date,
            "csa_hash": self.csa_hash,
        }


@dataclass
class Epic:
    formatted_id: str = ""
    name: str = ""
    description: str = ""
    integrations_text: str = ""  # free-text describing integration points (optional)
    acceptance_criteria: list[Any] = field(default_factory=list)
    nfrs: list[Any] = field(default_factory=list)
    scope_items: list[Any] = field(default_factory=list)  # list[ScopeItem]
    object_version: int | None = None
    last_update_date: str = ""

    @classmethod
    def from_payload(cls, p: dict[str, Any]) -> Epic:
        p = p or {}
        description = p.get("description", "")
        # The Modernization Scope table may be passed explicitly or embedded in the description.
        scope_src = p.get("modernization_scope_text") or description
        scope_items = parse_scope_table(scope_src)
        return cls(
            formatted_id=p.get("formatted_id") or p.get("formattedId") or "",
            name=p.get("name", ""),
            description=description,
            integrations_text=p.get("integrations_text", ""),
            acceptance_criteria=list(p.get("acceptance_criteria", []) or []),
            nfrs=list(p.get("nfrs", []) or []),
            scope_items=scope_items,
            object_version=p.get("object_version", p.get("objectVersion")),
            last_update_date=p.get("last_update_date", p.get("lastUpdateDate", "")),
        )

    def raw_text(self) -> str:
        parts = [self.name, self.description, self.integrations_text]
        parts += list(self.acceptance_criteria) + list(self.nfrs)
        return "\n".join(p for p in parts if p)

    def provenance(self, csa_hash: str = "") -> EpicProvenance:
        return EpicProvenance(
            formatted_id=self.formatted_id,
            object_version=self.object_version,
            last_update_date=self.last_update_date,
            csa_hash=csa_hash,
        )


@dataclass
class IntegrationSignal:
    """One integration point with up to eight span-traced signal fields."""

    int_id: str
    name: str = ""
    fields: dict[str, Any] = field(
        default_factory=dict
    )  # key -> {"value": str, "epic_span": str}
    target_intent: dict[str, Any] = field(
        default_factory=dict
    )  # optional {"value","epic_span"}

    @property
    def filled(self) -> int:
        return sum(1 for k in SIGNAL_KEYS if (self.fields.get(k) or {}).get("value"))

    @property
    def confidence(self) -> float:
        return round(min(1.0, self.filled / EXPECTED_SLOTS), 2)

    @property
    def needs_review(self) -> bool:
        return self.confidence < 0.85

    def to_dict(self) -> dict[str, Any]:
        return {
            "int_id": self.int_id,
            "name": self.name,
            "filled": self.filled,
            "expected_slots": EXPECTED_SLOTS,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
            "fields": {k: self.fields[k] for k in SIGNAL_KEYS if k in self.fields},
            **(
                {"target_intent": self.target_intent}
                if self.target_intent.get("value")
                else {}
            ),
        }


@dataclass
class BrownfieldEpicSignalLedger:
    provenance: EpicProvenance
    summary: dict[str, Any] = field(default_factory=dict)  # {"value","epic_span"}
    scope: dict[str, Any] = field(default_factory=dict)
    integrations: list[Any] = field(default_factory=list)  # list[IntegrationSignal]
    nfrs: list[Any] = field(default_factory=list)  # list[{"value","kind","epic_span"}]
    schema: str = LEDGER_SCHEMA

    def per_integration_confidence(self) -> dict[str, Any]:
        return {ig.int_id: ig.confidence for ig in self.integrations}

    def total_signals(self) -> int:
        base = sum(ig.filled for ig in self.integrations) + len(self.nfrs)
        return int(
            base
            + (1 if self.summary.get("value") else 0)
            + (1 if self.scope.get("value") else 0)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "provenance": self.provenance.to_dict(),
            "summary": self.summary,
            "modernization_scope": self.scope,
            "integrations": [ig.to_dict() for ig in self.integrations],
            "nfrs": self.nfrs,
        }


def empty_ledger(provenance: EpicProvenance) -> BrownfieldEpicSignalLedger:
    return BrownfieldEpicSignalLedger(provenance=provenance)
