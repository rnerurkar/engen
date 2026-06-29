"""Tool 1 — map_current_to_target: context-filtered tech substitution decision table.

DETERMINISTIC. NO LLM. lookup(source_tech, r_factor, context) against a rules table:
  - Most-specific matching row wins (most context dimensions matched).
  - priority field breaks specificity ties.
  - Remaining ties -> requires_review.
  - No matching row -> integration into unresolved[] and the tool errors (no LLM fallback).

The ceiling of 12 context dimensions is CI-enforced (see check_context_ceiling).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_CONTEXT_DIMENSIONS = 12


class UnresolvedSubstitutionError(Exception):
    """Raised when one or more integrations have no matching substitution row."""

    def __init__(self, unresolved: list[Any]) -> None:
        self.unresolved = unresolved
        super().__init__(
            f"{len(unresolved)} integration(s) have no matching substitution row: "
            f"{[u['integration_id'] for u in unresolved]}"
        )


@dataclass
class SubstitutionRow:
    source_tokens: list[Any]
    r_factor: str
    context_matched: dict[str, Any]
    target_tokens: list[Any]
    adr_ref: str = ""
    transition_pattern_ref: str = ""
    priority: int = 0
    confidence: float = 1.0


@dataclass
class Substitution:
    integration_id: str
    source_tokens: list[Any]
    r_factor: str
    context_matched: dict[str, Any]
    target_tokens: list[Any]
    adr_ref: str = ""
    transition_pattern_ref: str = ""
    confidence: float = 1.0
    requires_review: bool = False


def check_context_ceiling(rows: list[SubstitutionRow]) -> None:
    """CI guard: no row may exceed 12 context dimensions."""
    for r in rows:
        if len(r.context_matched) > MAX_CONTEXT_DIMENSIONS:
            raise ValueError(
                f"substitution row exceeds {MAX_CONTEXT_DIMENSIONS} context dimensions: "
                f"{list(r.context_matched)}"
            )


def _normalize(s: str) -> str:
    """Normalize a tech token for matching: lowercase, hyphens and spaces equivalent.
    'IBM API Connect' and 'ibm-api-connect' must match. This is deliberate — decision-table
    rows are authored with hyphenated slugs while specs use natural prose."""
    return s.lower().replace("-", " ")


def _row_matches(
    row: SubstitutionRow, source_tech: str, r_factor: str, context: dict[str, Any]
) -> int | None:
    """Return specificity score (n context dims matched) if the row matches, else None.
    A row matches if its source token appears in source_tech, r_factor matches, and every
    context dimension the row specifies is satisfied by the integration's context."""
    if row.r_factor != r_factor:
        return None
    st = _normalize(source_tech)
    if not any(_normalize(tok) in st for tok in row.source_tokens):
        return None
    for k, v in row.context_matched.items():
        if context.get(k, "").lower() != v.lower():
            return None
    return len(row.context_matched)  # specificity = number of context dims matched


def map_current_to_target(
    integrations: list[dict[str, Any]], rows: list[SubstitutionRow]
) -> dict[str, Any]:
    """integrations: [{integration_id, source_tech, r_factor, context}]. Returns
    {tech_substitutions: [...], unresolved: [...]}. Raises UnresolvedSubstitutionError if any
    integration is unresolved (forces the platform-engineering review queue)."""
    check_context_ceiling(rows)
    substitutions, unresolved = [], []

    for it in integrations:
        candidates = []
        for row in rows:
            score = _row_matches(
                row, it["source_tech"], it["r_factor"], it.get("context", {})
            )
            if score is not None:
                candidates.append((score, row.priority, row))
        if not candidates:
            unresolved.append(
                {
                    "integration_id": it["integration_id"],
                    "source_tech": it["source_tech"],
                    "r_factor": it["r_factor"],
                }
            )
            continue
        # Most-specific wins; priority breaks ties; detect unbroken ties.
        candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
        top = candidates[0]
        tie = (
            len(candidates) > 1
            and candidates[1][0] == top[0]
            and candidates[1][1] == top[1]
        )
        row = top[2]
        substitutions.append(
            Substitution(
                integration_id=it["integration_id"],
                source_tokens=row.source_tokens,
                r_factor=row.r_factor,
                context_matched=row.context_matched,
                target_tokens=row.target_tokens,
                adr_ref=row.adr_ref,
                transition_pattern_ref=row.transition_pattern_ref,
                confidence=row.confidence,
                requires_review=tie,
            )
        )

    if unresolved:
        # Surface partial results but signal the error per the documented failure mode.
        raise UnresolvedSubstitutionError(unresolved)
    return {
        "tech_substitutions": [s.__dict__ for s in substitutions],
        "unresolved": unresolved,
    }
