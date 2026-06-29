"""Pydantic v2 boundary models (§1.1) — validate structured LLM outputs and tool/skill definitions at
the boundary so dynamic model responses cannot corrupt agent state."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SignalModel(_Strict):
    """One extracted signal at the LLM→ledger boundary (greenfield + brownfield shaping)."""

    value: str = Field(min_length=1)
    epic_span: str = Field(min_length=1)
    kind: str = "signal"


class ToolDefinitionModel(_Strict):
    """Definition for a to-create FunctionTool (§1.1: Pydantic models for tool definitions)."""

    description: str = Field(min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class SkillDefinitionModel(_Strict):
    """Definition for a to-create skill (SKILL.md content)."""

    description: str = Field(min_length=1)
    skill_md: str = Field(min_length=1)


def validate_signals(raw: list[dict[str, Any]]) -> list[SignalModel]:
    """Validate a list of raw signal dicts; invalid entries raise pydantic.ValidationError."""
    return [SignalModel.model_validate(r) for r in (raw or [])]
