"""Generate eval/golden-dataset.json seeded from spec §10 acceptance criteria.
Constitution Rule 12: ≥10 entries/agent, ≥3 edge cases, ≥1 negative, 100% coverage.

The SEED structure is real; the per-agent example *content* is authored by the
developer (the generator emits a schema-valid skeleton with TODO markers).
"""
from __future__ import annotations

import json
from pathlib import Path


def generate_seed(blueprint_path: str, out_path: str) -> dict:
    """Emit a golden-dataset.json skeleton covering every agent in the blueprint."""
    bp = json.loads(Path(blueprint_path).read_text())

    def walk(node):
        yield node
        for c in node.get("children", []):
            yield from walk(c)

    agents = [a["name"] for a in walk(bp["adk_agent_tree"]["root"])]
    entries = []
    for agent in sorted(agents):
        # One labelled placeholder per agent; developer fills inputs/expected.
        entries.append({
            "agent": agent,
            "type": "happy_path",
            "input": "TODO: from spec §10 acceptance criteria",
            "expected": "TODO",
            "tags": ["seed"],
        })
    dataset = {
        "version": "1.0",
        "solution_id": bp["metadata"]["solution_id"],
        "threshold": 0.90,
        "coverage": {"agents": agents, "min_per_agent": 10, "min_edge_cases": 3, "min_negative": 1},
        "entries": entries,
        "_note": "Seed skeleton. Expand to ≥10/agent, ≥3 edge, ≥1 negative (Constitution Rule 12).",
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(dataset, indent=2))
    return dataset
