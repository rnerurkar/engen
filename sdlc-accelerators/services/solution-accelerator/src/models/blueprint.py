"""Pydantic models for app-blueprint.json.
Mirrors schemas/app-blueprint.schema.json — validated against examples/fnol.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AgentType = Literal["SequentialAgent", "ParallelAgent", "LoopAgent", "LlmAgent", "CustomAgent"]
ToolType = Literal["mcp_server", "a2a_agent", "function_tool"]


class RetryPolicy(BaseModel):
    type: str
    max_attempts: int = Field(ge=1)
    backoff: str


class AgentNode(BaseModel):
    name: str
    type: AgentType
    role: str
    model: str | None = None
    tools: list[str] = Field(default_factory=list)
    retry: RetryPolicy | None = None
    children: list[AgentNode] = Field(default_factory=list)


class ToolBinding(BaseModel):
    name: str
    type: ToolType
    assigned_to: str
    endpoint: str | None = None
    auth_method: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    discovered_via: str | None = None
    confidence: float | None = None


class BusinessRule(BaseModel):
    id: str
    rule: str
    implemented_by: str
    source: str | None = None


class ScreeningConfig(BaseModel):
    model_armor_level: str
    agents_with_input_screening: list[str]
    agents_with_output_screening: list[str]
    pii_categories_monitored: list[str] = Field(default_factory=list)
    blocked_output_patterns: list[str] = Field(default_factory=list)


class AgentIdentity(BaseModel):
    agent: str
    service_account: str
    capabilities: list[str]
    denied: list[str] = Field(default_factory=list)
    delegation: list[str] = Field(default_factory=list)


class AgentTree(BaseModel):
    root: AgentNode


class AppBlueprint(BaseModel):
    metadata: dict
    pattern_composition: dict
    adk_agent_tree: AgentTree
    tool_bindings: list[ToolBinding]
    business_rules: list[BusinessRule]
    agent_identity_config: list[AgentIdentity]
    screening_config: ScreeningConfig
    observability_config: dict
    infra_modules: list[dict] = Field(default_factory=list)
    hadr_config: dict = Field(default_factory=dict)
    nfr_targets: dict = Field(default_factory=dict)
    data_flows: list[dict] = Field(default_factory=list)
    sequence_summary: list = Field(default_factory=list)
    gateway_routes: list[dict] = Field(default_factory=list)
    pipeline_configs: dict = Field(default_factory=dict)
    confidence_scores: dict = Field(default_factory=dict)


AgentNode.model_rebuild()
