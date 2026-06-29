"""LlmAgent call harness for recommend_architecture.

Implements EVERYTHING around the model call:
  - loads the authored 8-step system prompt (prompts/greenfield-system-prompt.md)
  - assembles the user message (spec.md + plan.md + extracted signals + retrieved RAG context)
  - invokes the LlmAgent (the single seam marked TODO — the live Gemini call)
  - parses the model's structured output into ArchitectureSelections (validated)

The HARNESS is real and tested with a stubbed model. The model's REASONING is the authored
prompt running on Gemini — supplied at runtime, not fabricated here.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from assembly.selections import (
    AgentSelection,
    ArchitectureSelections,
    BusinessRuleSelection,
    PatternSelection,
    SkillSelection,
    ToolSelection,
)

PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "prompts",
    "greenfield-system-prompt.md",
)


@dataclass
class RetrievedContext:
    """RAG + API Hub retrieval results the prompt instructs the agent to use."""

    patterns: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    integrations: list[dict[str, Any]]  # MCP servers + A2A agents from API Hub


def load_system_prompt() -> str:
    with open(PROMPT_PATH) as f:
        return f.read()


def build_user_message(
    spec_md: str, plan_md: str, signals: dict[str, Any], ctx: RetrievedContext
) -> str:
    """Assemble the user turn: raw spec/plan markdown + extracted signals + retrieved context.
    Spec/plan are passed AS MARKDOWN (never converted to JSON) per the architecture."""
    return (
        "## spec.md\n" + spec_md.strip() + "\n\n"
        "## plan.md\n" + plan_md.strip() + "\n\n"
        "## Extracted signals (deterministic)\n"
        + json.dumps(signals, indent=2)
        + "\n\n"
        "## Retrieved pattern candidates (Vertex AI Search)\n"
        + json.dumps(ctx.patterns, indent=2)
        + "\n\n"
        "## Matched skill candidates (Vertex AI Search)\n"
        + json.dumps(ctx.skills, indent=2)
        + "\n\n"
        "## Discovered integrations (Apigee API Hub)\n"
        + json.dumps(ctx.integrations, indent=2)
        + "\n\n"
        "Produce the ArchitectureSelections as JSON following the 8 steps. Tag confidence on every "
        "selection; flag <0.85 as requires_review."
    )


def parse_selections(model_json: dict[str, Any]) -> ArchitectureSelections:
    """Parse the model's structured JSON output into a validated ArchitectureSelections."""

    def agent(node: dict[str, Any]) -> AgentSelection:
        return AgentSelection(
            name=node["name"],
            type=node["type"],
            role=node.get("role", ""),
            model=node.get("model"),
            tools=node.get("tools", []),
            retry=node.get("retry"),
            children=[agent(c) for c in node.get("children", [])],
        )

    return ArchitectureSelections(
        solution_id=model_json["solution_id"],
        use_case=model_json.get("use_case", ""),
        archetype=model_json.get("archetype", "agentic"),
        primary_pattern=model_json["primary_pattern"],
        pattern_composition=[
            PatternSelection(
                pattern=p["pattern"],
                role=p.get("role", ""),
                confidence=p.get("confidence", "medium"),
                source_pattern_id=p.get("source_pattern_id", ""),
                nesting=p.get("nesting"),
            )
            for p in model_json.get("pattern_composition", [])
        ],
        agent_tree=agent(model_json["agent_tree"]),
        tools=[
            ToolSelection(
                name=t["name"],
                type=t["type"],
                assigned_to=t["assigned_to"],
                endpoint=t.get("endpoint", ""),
                auth_method=t.get("auth_method", ""),
                capabilities=t.get("capabilities", []),
                discovered_via=t.get("discovered_via", ""),
                confidence=t.get("confidence"),
                status=t.get("status", "matched"),
                definition=t.get("definition"),
            )
            for t in model_json.get("tools", [])
        ],
        skills=[
            SkillSelection(
                name=s["name"],
                sha=s.get("sha", ""),
                version=s.get("version", ""),
                assigned_to=s.get("assigned_to", ""),
                status=s.get("status", "matched"),
                definition=s.get("definition"),
            )
            for s in model_json.get("skills", [])
        ],
        business_rules=[
            BusinessRuleSelection(
                id=b["id"],
                rule=b["rule"],
                implemented_by=b["implemented_by"],
                source=b.get("source", ""),
            )
            for b in model_json.get("business_rules", [])
        ],
        screening=model_json.get("screening", {}),
        agent_identity=model_json.get("agent_identity", []),
        infra_modules=model_json.get("infra_modules", []),
        hadr=model_json.get("hadr", {}),
        nfr_targets=model_json.get("nfr_targets", {}),
        observability=model_json.get("observability", {}),
        overall_confidence=model_json.get("overall_confidence", "medium"),
    )


def invoke_llm_agent(
    system_prompt: str,
    user_message: str,
    model_fn: Callable[[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Invoke the LlmAgent reasoning. Resolution order:
      1. an injected model_fn (tests / custom provider), else
      2. the WIRED live Gemini provider (reasoning.llm_provider) when configured, else
      3. a clear, actionable error explaining how to enable the live path.

    The system_prompt is the human-authored curated reasoning prompt, bound verbatim.
    """
    if model_fn is not None:
        return model_fn(system_prompt, user_message)
    return _live_invoke(system_prompt, user_message)


def _live_invoke(system_prompt: str, user_message: str) -> dict[str, Any]:
    """The WIRED live reasoning call via the Gemini provider (reasoning.llm_provider.invoke).

    This is active code (no longer commented out). It is configured via env:
      - GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT (+ ADC, Vertex AI User role,
        egress to aiplatform.googleapis.com), OR
      - GEMINI_API_KEY for the direct Gemini API.
      - SDLC_LLM_MODEL overrides the model (default gemini-2.5-pro).
    The provider requests response_mime_type=application/json so the parser gets a clean dict,
    and wraps the call in with_retry. When the SDK/credentials aren't present, it raises a clear
    error (callers in tests inject model_fn instead).
    """
    from reasoning.llm_provider import available, invoke

    ok, reason = available()
    if not ok:
        raise NotImplementedError(
            f"Live LLM reasoning is wired but not configured in this environment: {reason}. "
            "Configure credentials (see reasoning/llm_provider.py), or pass model_fn in tests."
        )
    # §2.1/§2.2/§3.1/§3.2/§5.2 — route the provider through the shared runtime: bounded exponential-backoff
    # retry, circuit breaker with secondary-model fallback, pooled async client, and a generation span.
    import asyncio

    from runtime import invoke_llm
    from runtime.reliability import TransientLLMError

    async def _provider(
        system_prompt_: str, user_message_: str, model_: str
    ) -> dict[str, Any]:
        try:
            return await asyncio.to_thread(invoke, system_prompt_, user_message_)
        except Exception as e:  # noqa: BLE001 — map transient transport errors to the retryable type
            name = type(e).__name__.lower()
            if any(
                t in name
                for t in ("timeout", "status", "connect", "transient", "ratelimit")
            ):
                raise TransientLLMError(str(e)) from e
            raise

    return invoke_llm(
        system_prompt,
        user_message,
        provider=_provider,
        agent_id="solution_accelerator_agent",
    )
