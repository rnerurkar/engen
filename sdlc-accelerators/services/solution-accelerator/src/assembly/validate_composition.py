"""validate_composition — the named MCP tool for pattern-tree adjacency validation.

Deterministic. Checks the composed agent tree against the pattern adjacency rules
(e.g. LoopAgent cannot nest directly inside ParallelAgent) before assembly proceeds.
Previously the logic lived only inside refresh/assembly; this exposes it as the tool
the architecture's tool table defines.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CompositionViolation:
    rule: str
    detail: str


@dataclass
class CompositionResult:
    valid: bool
    violations: list[CompositionViolation] = field(default_factory=list)


# Adjacency rules: (parent_type, child_type) pairs that are FORBIDDEN.
FORBIDDEN_ADJACENCY = {
    ("ParallelAgent", "LoopAgent"),   # LoopAgent cannot nest directly inside ParallelAgent
}


def validate_composition(agent_tree: dict) -> CompositionResult:
    """Validate a composed agent tree's pattern adjacency. agent_tree = {"root": {...}}."""
    result = CompositionResult(valid=True)
    root = agent_tree.get("root", agent_tree)

    def walk(node, parent_type=None):
        ntype = node.get("type")
        if parent_type and (parent_type, ntype) in FORBIDDEN_ADJACENCY:
            result.valid = False
            result.violations.append(CompositionViolation(
                rule=f"{ntype} cannot nest directly inside {parent_type}",
                detail=f"agent '{node.get('name')}' ({ntype}) under '{parent_type}'",
            ))
        for child in node.get("children", []):
            walk(child, ntype)

    walk(root)
    return result
