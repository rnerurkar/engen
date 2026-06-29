"""Brownfield Epic-to-Spec data models.

Unlike greenfield (a flat 10-section spec), the brownfield spec is INTEGRATION-INVENTORY shaped:
each integration carries the eight migration-readiness signals the brownfield `validate_spec` gate
checks. The Brownfield Epic Signal Ledger is therefore **integration-keyed**: one entry per
integration, each with up to eight span-traced signal fields, plus application Summary, Modernization
Scope, and application-wide NFRs.

Extractive + span-grounded (same guarantee as greenfield): every signal carries a verbatim `epic_span`
and a value grounded in that span; a deterministic validator drops the rest. Confidence per integration
= filled signal fields / 8 (deterministic fill ratio), which aligns with the 8-signal readiness gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LEDGER_SCHEMA = "brownfield-epic-signal-ledger/v1"

# The eight migration-readiness signal fields per integration (keys → spec.md labels).
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


@dataclass
class EpicProvenance:
    formatted_id: str = ""
    object_version: int | None = None
    last_update_date: str = ""
    source: str = "rally"

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "formatted_id": self.formatted_id,
            "object_version": self.object_version,
            "last_update_date": self.last_update_date,
        }


@dataclass
class Epic:
    formatted_id: str = ""
    name: str = ""
    description: str = ""
    integrations_text: str = ""  # free-text describing integration points (optional)
    acceptance_criteria: list[Any] = field(default_factory=list)
    nfrs: list[Any] = field(default_factory=list)
    object_version: int | None = None
    last_update_date: str = ""

    @classmethod
    def from_payload(cls, p: dict[str, Any]) -> Epic:
        p = p or {}
        return cls(
            formatted_id=p.get("formatted_id") or p.get("formattedId") or "",
            name=p.get("name", ""),
            description=p.get("description", ""),
            integrations_text=p.get("integrations_text", ""),
            acceptance_criteria=list(p.get("acceptance_criteria", []) or []),
            nfrs=list(p.get("nfrs", []) or []),
            object_version=p.get("object_version", p.get("objectVersion")),
            last_update_date=p.get("last_update_date", p.get("lastUpdateDate", "")),
        )

    def raw_text(self) -> str:
        parts = [self.name, self.description, self.integrations_text]
        parts += list(self.acceptance_criteria) + list(self.nfrs)
        return "\n".join(p for p in parts if p)

    def provenance(self) -> EpicProvenance:
        return EpicProvenance(
            formatted_id=self.formatted_id,
            object_version=self.object_version,
            last_update_date=self.last_update_date,
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
