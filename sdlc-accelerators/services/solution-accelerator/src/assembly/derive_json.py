"""Derive app-blueprint.json from ArchitectureSelections + spec/plan hashes.
Deterministic. Output validates against schemas/app-blueprint.schema.json.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .selections import AgentSelection, ArchitectureSelections


def _least_privilege(t: Any) -> str:
    """§6.1 — minimum role for a tool: read-only unless its capabilities imply writes."""
    from runtime.safety import least_privilege_role

    writes = any(
        "write" in (c or "").lower()
        or "update" in (c or "").lower()
        or "create" in (c or "").lower()
        for c in (t.capabilities or [])
    )
    return least_privilege_role(t.type, writes=writes)


def _valid_tool_def(definition: Any) -> dict[str, Any]:
    """§1.1 — validate a to-create FunctionTool definition at the boundary (Pydantic v2)."""
    from runtime.schemas import ToolDefinitionModel

    return ToolDefinitionModel.model_validate(definition or {}).model_dump()


def _valid_skill_def(definition: Any) -> dict[str, Any]:
    """§1.1 — validate a to-create skill (SKILL.md) definition at the boundary (Pydantic v2)."""
    from runtime.schemas import SkillDefinitionModel

    return SkillDefinitionModel.model_validate(definition or {}).model_dump()


def _hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _agent_node(a: AgentSelection) -> dict[str, Any]:
    node: dict[str, Any] = {"name": a.name, "type": a.type, "role": a.role}
    if a.model is not None:
        node["model"] = a.model
    if a.tools:
        node["tools"] = list(a.tools)
    if a.retry:
        node["retry"] = a.retry
    node["children"] = [_agent_node(c) for c in a.children]
    return node


def derive_json(
    sel: ArchitectureSelections, spec: str, plan: str, blueprint_md: str
) -> dict[str, Any]:
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
                    "pattern": p.pattern,
                    "role": p.role,
                    "confidence": _conf(p.confidence),
                    **({"nesting": p.nesting} if p.nesting else {}),
                    **(
                        {"source_signal": p.source_pattern_id}
                        if p.source_pattern_id
                        else {}
                    ),
                }
                for p in sel.pattern_composition
            ],
            "adjacency_validation": "PASSED",
        },
        "adk_agent_tree": {"root": _agent_node(sel.agent_tree)},
        "tool_bindings": [
            {
                k: v
                for k, v in {
                    "name": t.name,
                    "type": t.type,
                    "assigned_to": t.assigned_to,
                    "endpoint": t.endpoint or None,
                    "auth_method": t.auth_method or None,
                    "capabilities": t.capabilities or [],
                    "discovered_via": t.discovered_via or None,
                    "confidence": t.confidence,
                    "status": t.status,
                    # §6.1 least privilege — default read-only unless the tool's capabilities imply writes.
                    "least_privilege": _least_privilege(t),
                    "definition": _valid_tool_def(t.definition)
                    if t.status == "to_create"
                    else None,
                }.items()
                if v is not None
            }
            for t in sel.tools
        ],
        # No-match resolution (A2A > MCP > Build). The coding agent reads `to_create` and CREATES these:
        #   - each skill → write skills/<name>/SKILL.md from definition.skill_md
        #   - each function_tool → implement a new ADK FunctionTool from its definition (I/O schema)
        # Definitions are validated at the boundary with Pydantic v2 (§1.1).
        "to_create": {
            "skills": [
                {
                    "name": s.name,
                    "assigned_to": s.assigned_to,
                    "definition": _valid_skill_def(s.definition),
                }
                for s in sel.skills
                if s.status == "to_create"
            ],
            "function_tools": [
                {
                    "name": t.name,
                    "assigned_to": t.assigned_to,
                    "reason": "no A2A agent or MCP tool matched in API Hub",
                    "definition": _valid_tool_def(t.definition),
                }
                for t in sel.tools
                if t.status == "to_create"
            ],
        },
        "business_rules": [
            {
                "id": br.id,
                "rule": br.rule,
                "implemented_by": br.implemented_by,
                **({"source": br.source} if br.source else {}),
            }
            for br in sel.business_rules
        ],
        "agent_identity_config": sel.agent_identity,
        "screening_config": sel.screening,
        "observability_config": sel.observability,
        "infra_modules": sel.infra_modules,
        "hadr_config": sel.hadr,
        "nfr_targets": sel.nfr_targets,
        # skills carried with provenance (matched) or a SKILL.md definition (to_create) for /generate
        "skills": [
            {
                k: v
                for k, v in {
                    "name": s.name,
                    "assigned_to": s.assigned_to,
                    "status": s.status,
                    "sha": s.sha or None,
                    "version": s.version or None,
                    "definition": s.definition if s.status == "to_create" else None,
                }.items()
                if v is not None
            }
            for s in sel.skills
        ],
        "confidence_scores": {"overall": sel.overall_confidence},
    }


def _conf(c: str) -> float:
    return {"high": 0.95, "medium": 0.85, "low": 0.7}.get(c, 0.85)
