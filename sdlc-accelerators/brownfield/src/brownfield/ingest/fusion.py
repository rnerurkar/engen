"""Phase A fusion — cross-walk the Epic's modernization intent against CSA ground truth.

The component ID is the join key. Every component named in the Epic's Modernization Scope table must
resolve to a real component in the CSA registry; if it does not, you cannot modernize something that
isn't in the current state, so it is surfaced as a hard CLARIFY/BLOCK. CSA components the Epic does not
name are recorded as explicitly out-of-scope, so the generated spec is honest about its boundaries.

Deterministic: (epic scope, CSA registry) -> ResolvedScope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from brownfield.ingest.csa_loader import CsaComponent, CsaRegistry
from brownfield.ingest.epic_models import ScopeItem


@dataclass
class ResolvedUnit:
    """One in-scope modernization unit: an Epic disposition bound to a real CSA component."""

    component: CsaComponent
    scope: ScopeItem

    @property
    def component_id(self) -> str:
        return self.component.component_id

    @property
    def disposition(self) -> str | None:
        return self.scope.disposition


@dataclass
class ResolvedScope:
    in_scope: list[Any] = field(default_factory=list)  # list[ResolvedUnit]
    out_of_scope: list[str] = field(
        default_factory=list
    )  # CSA-COMP ids not named by the Epic
    unresolved: list[str] = field(
        default_factory=list
    )  # Epic ids with no CSA component
    invalid_disposition: list[str] = field(
        default_factory=list
    )  # in-scope but bad disposition

    @property
    def in_scope_ids(self) -> set[str]:
        return {u.component_id for u in self.in_scope}

    @property
    def blocked(self) -> bool:
        """A scope that names components the CSA doesn't contain, or no in-scope units at all,
        cannot be turned into a trustworthy modernization spec."""
        return bool(self.unresolved) or not self.in_scope

    def to_dict(self) -> dict[str, Any]:
        return {
            "in_scope": [
                {
                    "component_id": u.component_id,
                    "name": u.component.name,
                    "disposition": u.disposition,
                    "aws_target": u.scope.aws_target,
                    "rationale": u.scope.rationale,
                }
                for u in self.in_scope
            ],
            "out_of_scope": self.out_of_scope,
            "unresolved": self.unresolved,
            "invalid_disposition": self.invalid_disposition,
        }


def cross_walk(scope_items: list[Any], registry: CsaRegistry) -> ResolvedScope:
    """Resolve the Epic's scope table against the CSA registry into in/out/unresolved buckets."""
    rs = ResolvedScope()
    named: set[str] = set()
    for item in scope_items:
        cid = item.component_id.upper()
        named.add(cid)
        comp = registry.components.get(cid)
        if comp is None:
            rs.unresolved.append(cid)
            continue
        rs.in_scope.append(ResolvedUnit(component=comp, scope=item))
        if not item.valid_disposition:
            rs.invalid_disposition.append(cid)
    rs.in_scope.sort(key=lambda u: u.component_id)
    rs.out_of_scope = sorted(cid for cid in registry.components if cid not in named)
    return rs
