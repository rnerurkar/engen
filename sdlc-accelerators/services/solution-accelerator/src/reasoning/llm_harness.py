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
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "prompts", "greenfield-system-prompt.md"
)


@dataclass
class RetrievedContext:
    """RAG + API Hub retrieval results the prompt instructs the agent to use."""
    patterns: list[dict]
    skills: list[dict]
    integrations: list[dict]   # MCP servers + A2A agents from API Hub


def load_system_prompt() -> str:
    with open(PROMPT_PATH) as f:
        return f.read()


def build_user_message(spec_md: str, plan_md: str, signals: dict, ctx: RetrievedContext) -> str:
    """Assemble the user turn: raw spec/plan markdown + extracted signals + retrieved context.
    Spec/plan are passed AS MARKDOWN (never converted to JSON) per the architecture."""
    return (
        "## spec.md\n" + spec_md.strip() + "\n\n"
        "## plan.md\n" + plan_md.strip() + "\n\n"
        "## Extracted signals (deterministic)\n" + json.dumps(signals, indent=2) + "\n\n"
        "## Retrieved pattern candidates (Vertex AI Search)\n" + json.dumps(ctx.patterns, indent=2) + "\n\n"
        "## Matched skill candidates (Vertex AI Search)\n" + json.dumps(ctx.skills, indent=2) + "\n\n"
        "## Discovered integrations (Apigee API Hub)\n" + json.dumps(ctx.integrations, indent=2) + "\n\n"
        "Produce the ArchitectureSelections as JSON following the 8 steps. Tag confidence on every "
        "selection; flag <0.85 as requires_review."
    )


def parse_selections(model_json: dict) -> ArchitectureSelections:
    """Parse the model's structured JSON output into a validated ArchitectureSelections."""
    def agent(node: dict) -> AgentSelection:
        return AgentSelection(
            name=node["name"], type=node["type"], role=node.get("role", ""),
            model=node.get("model"), tools=node.get("tools", []), retry=node.get("retry"),
            children=[agent(c) for c in node.get("children", [])],
        )

    return ArchitectureSelections(
        solution_id=model_json["solution_id"],
        use_case=model_json.get("use_case", ""),
        archetype=model_json.get("archetype", "agentic"),
        primary_pattern=model_json["primary_pattern"],
        pattern_composition=[
            PatternSelection(pattern=p["pattern"], role=p.get("role", ""),
                             confidence=p.get("confidence", "medium"),
                             source_pattern_id=p.get("source_pattern_id", ""),
                             nesting=p.get("nesting"))
            for p in model_json.get("pattern_composition", [])
        ],
        agent_tree=agent(model_json["agent_tree"]),
        tools=[
            ToolSelection(name=t["name"], type=t["type"], assigned_to=t["assigned_to"],
                          endpoint=t.get("endpoint", ""), auth_method=t.get("auth_method", ""),
                          capabilities=t.get("capabilities", []),
                          discovered_via=t.get("discovered_via", ""), confidence=t.get("confidence"))
            for t in model_json.get("tools", [])
        ],
        skills=[
            SkillSelection(name=s["name"], sha=s.get("sha", ""), version=s.get("version", ""),
                           assigned_to=s.get("assigned_to", ""))
            for s in model_json.get("skills", [])
        ],
        business_rules=[
            BusinessRuleSelection(id=b["id"], rule=b["rule"], implemented_by=b["implemented_by"],
                                  source=b.get("source", ""))
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


def invoke_llm_agent(system_prompt: str, user_message: str,
                     model_fn: Callable[[str, str], dict] | None = None) -> dict:
    """Invoke the LlmAgent. The single live seam.

    model_fn lets tests inject a deterministic model. In production, model_fn wraps the
    ADK LlmAgent / Gemini call with response_mime_type=application/json.
    """
    if model_fn is not None:
        return model_fn(system_prompt, user_message)
    return _live_invoke(system_prompt, user_message)


def _live_invoke(system_prompt: str, user_message: str) -> dict:
    """The actual ADK LlmAgent (Gemini) call. COMMENTED OUT until wired.

    TO WIRE (checklist):
      1. `pip install google-adk` (the Agent Development Kit) — or `google-genai` if calling
         Gemini directly without ADK.
      2. Supply the model id (e.g. gemini-2.5-pro) and the GCP project/location for Vertex AI.
      3. Credentials: Application Default Credentials (ADC) with the Vertex AI User role.
      4. Ensure egress to aiplatform.googleapis.com (Vertex AI).
      5. Request JSON output (response_mime_type=application/json) so the parser downstream
         receives a clean dict. Uncomment the body and wrap the model call in with_retry(...).

    NOTE (prompt is authored IP): the system_prompt passed here is the human-authored curated
    reasoning prompt loaded from prompts/greenfield-system-prompt.md — do NOT inline or mutate
    it here; bind it as the agent's instruction verbatim.
    """
    # import json
    # from google.adk.agents import LlmAgent
    # from google.adk.runners import InMemoryRunner
    # from clients.base import with_retry
    #
    # agent = LlmAgent(
    #     model="gemini-2.5-pro",
    #     name="solution_architect",
    #     instruction=system_prompt,          # the authored prompt, verbatim
    #     generate_content_config={"response_mime_type": "application/json"},
    # )
    # runner = InMemoryRunner(agent=agent)
    #
    # def _call() -> dict:
    #     events = runner.run(user_message)            # drive the agent to completion
    #     final_text = events[-1].content.parts[0].text
    #     return json.loads(final_text)                # JSON output -> dict
    #
    # return with_retry(_call)
    raise NotImplementedError(
        "ADK LlmAgent (Gemini) call is written but commented out in _live_invoke. "
        "Uncomment it (+ google-adk + model id + credentials), or pass model_fn in tests."
    )
