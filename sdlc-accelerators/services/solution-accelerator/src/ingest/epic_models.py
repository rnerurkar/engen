"""Epic-to-Spec ingestion — data models (Greenfield front door).

The `ingest_epic` tool turns a Rally Epic into a signal-bearing `spec.md`:

  Phase A (agentic shaping)   — the ONE LlmAgent normalizes the Epic's linguistic signals into a
                                section-keyed Epic Signal Ledger (extractive; span-traced + value-grounded; cannot fabricate/alter).
  Phase B (deterministic map) — renders the 10-section spec.md from the ledger, computes per-section
                                confidence from the signal-slot FILL RATIO, stamps Rally provenance.

IP boundary: this REUSES the single recommend_architecture LlmAgent for a second, bounded, extractive
invocation. It is NOT the external platform's Epic-IR / dedicated ingestion agent / cosign attestation — different
mechanism, zero claim overlap. The ledger is section-keyed (vs adjacent external IP's requirement-objects), and
confidence is a deterministic fill ratio (vs agent-reported).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# The 10 spec.md sections (must match .specify/templates/spec-template.md), each with the deterministic
# number of signal slots Phase B expects. Per-section confidence = min(1.0, filled / expected_slots).
# `optional=True` means an empty section is legitimate (a low score there should not force a redo).
@dataclass(frozen=True)
class SectionDef:
    num: int
    key: str
    title: str
    expected_slots: int
    optional: bool = False


SECTIONS: list[SectionDef] = [
    SectionDef(1, "use_case_actors", "Use Case & Actors", 2),
    SectionDef(2, "workflow_ordering", "Workflow Ordering", 3),
    SectionDef(3, "scope_throughput_latency", "Scope, Throughput & Latency", 3),
    SectionDef(4, "data_sources", "Data Sources", 2),
    SectionDef(5, "external_partners", "External Partners", 1, optional=True),
    SectionDef(6, "actors_permissions", "Actors & Permissions", 1),
    SectionDef(7, "business_rules", "Business Rules (IF/THEN)", 2),
    SectionDef(8, "error_handling", "Error Handling & Edge Cases", 1),
    SectionDef(9, "nfrs", "Non-Functional Requirements", 2),
    SectionDef(10, "acceptance_criteria", "Acceptance Criteria", 3),
]

SECTION_BY_NUM: dict[int, SectionDef] = {s.num: s for s in SECTIONS}
VALID_SECTION_NUMS: set[int] = set(SECTION_BY_NUM)


@dataclass
class Epic:
    """A Rally Epic as fetched CLIENT-SIDE by the coding agent (via the Rally MCP server) and handed to
    ingest_epic. Contains epic CONTENT only — never Rally credentials. `raw_text` is the concatenation
    the deterministic validator checks signal spans against (extractive guarantee)."""

    formatted_id: str = ""
    name: str = ""
    description: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    nfrs: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    linked_items: list[str] = field(default_factory=list)
    object_version: int | None = None
    last_update_date: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Epic:
        def _list(v: Any) -> list[str]:
            if v is None:
                return []
            if isinstance(v, str):
                return [v]
            return [str(x) for x in v]

        return cls(
            formatted_id=str(
                payload.get("formatted_id") or payload.get("FormattedID") or ""
            ),
            name=str(payload.get("name") or payload.get("Name") or ""),
            description=str(
                payload.get("description") or payload.get("Description") or ""
            ),
            acceptance_criteria=_list(
                payload.get("acceptance_criteria") or payload.get("AcceptanceCriteria")
            ),
            nfrs=_list(payload.get("nfrs") or payload.get("NFRs")),
            dependencies=_list(
                payload.get("dependencies") or payload.get("Dependencies")
            ),
            linked_items=_list(
                payload.get("linked_items") or payload.get("LinkedItems")
            ),
            object_version=payload.get("object_version")
            if payload.get("object_version") is not None
            else payload.get("ObjectVersion"),
            last_update_date=str(
                payload.get("last_update_date") or payload.get("LastUpdateDate") or ""
            ),
        )

    def raw_text(self) -> str:
        """All Epic prose concatenated — the corpus the validator verifies signal spans against."""
        parts = [
            self.name,
            self.description,
            *self.acceptance_criteria,
            *self.nfrs,
            *self.dependencies,
            *self.linked_items,
        ]
        return "\n".join(p for p in parts if p)


@dataclass
class LedgerSignal:
    """One extracted signal. `epic_span` is a VERBATIM snippet of the Epic — the validator drops any
    signal whose span is not in the Epic or whose value is not grounded in that span — how the agent 'cannot fabricate/alter'."""

    value: str
    kind: str
    epic_span: str

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "kind": self.kind, "epic_span": self.epic_span}


@dataclass
class LedgerSection:
    num: int
    key: str
    title: str
    expected_slots: int
    optional: bool
    signals: list[LedgerSignal] = field(default_factory=list)

    @property
    def filled(self) -> int:
        return len(self.signals)

    @property
    def confidence(self) -> float:
        """Fill ratio (deterministic) — NOT an LLM self-assessment."""
        if self.expected_slots <= 0:
            return 1.0
        return round(min(1.0, self.filled / self.expected_slots), 2)

    @property
    def needs_review(self) -> bool:
        # Below 0.85 mirrors the blueprint requires_review threshold; optional+empty does not force review.
        if self.optional and self.filled == 0:
            return False
        return self.confidence < 0.85

    def to_dict(self) -> dict[str, Any]:
        return {
            "num": self.num,
            "key": self.key,
            "title": self.title,
            "expected_slots": self.expected_slots,
            "filled": self.filled,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
            "optional": self.optional,
            "signals": [s.to_dict() for s in self.signals],
        }


@dataclass
class EpicProvenance:
    source: str = "rally"
    formatted_id: str = ""
    object_version: int | None = None
    last_update_date: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "formatted_id": self.formatted_id,
            "object_version": self.object_version,
            "last_update_date": self.last_update_date,
        }


@dataclass
class EpicSignalLedger:
    """Section-keyed, span-traced ledger produced by Phase A and consumed by Phase B."""

    provenance: EpicProvenance
    sections: list[LedgerSection]

    def section(self, num: int) -> LedgerSection | None:
        for s in self.sections:
            if s.num == num:
                return s
        return None

    def per_section_confidence(self) -> dict[str, float]:
        return {f"§{s.num} {s.title}": s.confidence for s in self.sections}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "epic-signal-ledger/v1",
            "provenance": self.provenance.to_dict(),
            "sections": [s.to_dict() for s in self.sections],
        }


def empty_ledger(provenance: EpicProvenance) -> EpicSignalLedger:
    return EpicSignalLedger(
        provenance=provenance,
        sections=[
            LedgerSection(s.num, s.key, s.title, s.expected_slots, s.optional)
            for s in SECTIONS
        ],
    )
