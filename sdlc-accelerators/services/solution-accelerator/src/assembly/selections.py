"""ArchitectureSelections — the structured output of recommend_architecture (LLM reasoning).

recommend_architecture (the RAG-grounded LlmAgent) emits this after composing retrieved
patterns + discovered tools/agents + matched skills. assemble_blueprint (deterministic)
consumes it to build app-blueprint.md/.json + Eraser DSL.

This is the contract BETWEEN the reasoning stage and the deterministic assembly stage.
The reasoning that FILLS it is human-authored (system prompt); the assembly that CONSUMES
it is the deterministic code in this package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Confidence = Literal["high", "medium", "low"]


@dataclass
class PatternSelection:
    pattern: str  # e.g. "SequentialAgent"
    role: str
    confidence: Confidence
    source_pattern_id: str = ""  # provenance: which catalog pattern (RAG hit)
    nesting: str | None = None


@dataclass
class AgentSelection:
    name: str
    type: str  # SequentialAgent | ParallelAgent | LoopAgent | LlmAgent | CustomAgent
    role: str
    model: str | None = None
    tools: list[str] = field(default_factory=list)
    retry: dict[str, Any] | None = None
    children: list[AgentSelection] = field(default_factory=list)


@dataclass
class ToolSelection:
    name: str
    type: Literal["mcp_server", "a2a_agent", "function_tool"]
    assigned_to: str
    endpoint: str = ""
    auth_method: str = ""
    capabilities: list[str] = field(default_factory=list)
    discovered_via: str = (
        ""  # "Apigee API Hub" | "Vertex AI Search" | "spec" | "none (to_create)"
    )
    confidence: float | None = None
    # Resolution status (A2A > MCP > Build). "matched" = an existing A2A agent or MCP tool was found in
    # API Hub; "to_create" = NO match at any tier, so the coding agent must BUILD a new FunctionTool from
    # `definition`. A to_create tool MUST be type "function_tool".
    status: Literal["matched", "to_create"] = "matched"
    definition: dict[str, Any] | None = None  # for to_create function_tools:
    #   {description, input_schema, output_schema, rationale}


@dataclass
class SkillSelection:
    name: str
    assigned_to: str = ""  # which agent this skill informs
    sha: str = ""  # provenance for a MATCHED catalog skill (empty when to_create)
    version: str = ""  # provenance for a MATCHED catalog skill (empty when to_create)
    # "matched" = found in the Skill Catalog (Vertex AI Search) with sha+version; "to_create" = NO catalog
    # match, so the coding agent must CREATE a new skill from `definition` (a full SKILL.md).
    status: Literal["matched", "to_create"] = "matched"
    definition: dict[str, Any] | None = (
        None  # for to_create skills: {description, skill_md}  (skill_md = SKILL.md)
    )


@dataclass
class BusinessRuleSelection:
    id: str
    rule: str
    implemented_by: str
    source: str = ""


@dataclass
class ArchitectureSelections:
    """Everything recommend_architecture composed. The complete reasoning output."""

    solution_id: str
    use_case: str
    archetype: str
    primary_pattern: str
    pattern_composition: list[PatternSelection]
    agent_tree: AgentSelection
    tools: list[ToolSelection]
    skills: list[SkillSelection]
    business_rules: list[BusinessRuleSelection]
    # config carried from plan.md / spec.md
    screening: dict[str, Any] = field(default_factory=dict)
    agent_identity: list[dict[str, Any]] = field(default_factory=list)
    infra_modules: list[dict[str, Any]] = field(default_factory=list)
    hadr: dict[str, Any] = field(default_factory=dict)
    nfr_targets: dict[str, Any] = field(default_factory=dict)
    observability: dict[str, Any] = field(default_factory=dict)
    overall_confidence: Confidence = "medium"


AgentSelection.__pydantic_complete__ = True  # type: ignore[attr-defined]  # pydantic internal
