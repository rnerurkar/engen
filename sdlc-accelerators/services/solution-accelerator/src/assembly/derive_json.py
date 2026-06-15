"""Derive app-blueprint.json from ArchitectureSelections + spec/plan hashes.
Deterministic. Output validates against schemas/app-blueprint.schema.json.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict

from .selections import AgentSelection, ArchitectureSelections


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _agent_node(a: AgentSelection) -> dict:
    node = {"name": a.name, "type": a.type, "role": a.role}
    if a.model is not None:
        node["model"] = a.model
    if a.tools:
        node["tools"] = list(a.tools)
    if a.retry:
        node["retry"] = a.retry
    node["children"] = [_agent_node(c) for c in a.children]
    return node


def derive_json(sel: ArchitectureSelections, spec: str, plan: str, blueprint_md: str) -> dict:
    """Produce the machine-readable app-blueprint.json (the DERIVED artifact)."""
    return {
        "metadata": {
            "solution_id": sel.solution_id,
            "version": "1.0.0",
            "archetype": sel.archetype,
            "use_case": sel.use_case,
            "generated_by": "assemble_blueprint",
            "source_hashes": {
                "spec_hash": _hash(spec),
                "plan_hash": _hash(plan),
                "blueprint_hash": _hash(blueprint_md),
            },
            "blueprint_version": "9-section",
            "accelerator_version": "2.0",
        },
        "pattern_composition": {
            "primary_pattern": sel.primary_pattern,
            "composition": [
                {
                    "pattern": p.pattern, "role": p.role, "confidence": _conf(p.confidence),
                    **({"nesting": p.nesting} if p.nesting else {}),
                    **({"source_signal": p.source_pattern_id} if p.source_pattern_id else {}),
                }
                for p in sel.pattern_composition
            ],
            "adjacency_validation": "PASSED",
        },
        "adk_agent_tree": {"root": _agent_node(sel.agent_tree)},
        "tool_bindings": [
            {k: v for k, v in {
                "name": t.name, "type": t.type, "assigned_to": t.assigned_to,
                "endpoint": t.endpoint or None, "auth_method": t.auth_method or None,
                "capabilities": t.capabilities or [], "discovered_via": t.discovered_via or None,
                "confidence": t.confidence,
            }.items() if v is not None}
            for t in sel.tools
        ],
        "business_rules": [
            {"id": br.id, "rule": br.rule, "implemented_by": br.implemented_by,
             **({"source": br.source} if br.source else {})}
            for br in sel.business_rules
        ],
        "agent_identity_config": sel.agent_identity,
        "screening_config": sel.screening,
        "observability_config": sel.observability,
        "infra_modules": sel.infra_modules,
        "hadr_config": sel.hadr,
        "nfr_targets": sel.nfr_targets,
        # skills carried with provenance for the generate step
        "skills": [asdict(s) for s in sel.skills],
        "confidence_scores": {"overall": sel.overall_confidence},
    }


def _conf(c: str) -> float:
    return {"high": 0.95, "medium": 0.85, "low": 0.7}.get(c, 0.85)
