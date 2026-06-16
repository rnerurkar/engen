"""Greenfield blueprint orchestrator — an ADK SequentialAgent exposing the existing pipeline.

This wraps the ALREADY-TESTED greenfield reasoning pipeline as an ADK SequentialAgent for
observability, agent identity, and Model Armor callbacks — WITHOUT changing the pipeline's
contract. The ONE reasoning stage is an ADK LlmAgent; every other stage stays deterministic.

Agent names (distinct from brownfield):
  - SequentialAgent:  "greenfield_blueprint_orchestrator"
  - reasoning LlmAgent: "greenfield_architecture_recommender"

ADK is import-guarded: `build_orchestrator()` constructs the real ADK agents when google-adk is
installed; `available()` reports whether that path is usable. The deterministic stages reuse the
tested functions in this package (recommend_architecture.RecommendArchitecture) — assembly remains
deterministic and only CALLS the Eraser MCP tool to render diagrams (no LLM authorship of artifacts).
"""
from __future__ import annotations

SEQUENTIAL_AGENT_NAME = "greenfield_blueprint_orchestrator"
RECOMMENDER_AGENT_NAME = "greenfield_architecture_recommender"


def available() -> tuple[bool, str]:
    """Is the ADK orchestrator path usable here?"""
    try:
        import google.adk.agents  # noqa: F401
    except ImportError:
        return False, "google-adk not installed (pip install google-adk)"
    return True, ""


def build_recommender_agent(model: str = "gemini-2.5-pro", instruction: str = "",
                            search_client=None):
    """Build the single reasoning sub-agent (an ADK LlmAgent). The instruction is the
    human-authored curated prompt, bound verbatim. Pattern retrieval (Vertex AI Search over the
    Pattern Catalog) is attached as an ADK FunctionTool — the recommender decides what to query
    and when, then reasons over the candidates. search_client is injectable for tests."""
    from google.adk.agents import LlmAgent

    from .pattern_search_tool import make_pattern_search_tool
    pattern_tool = make_pattern_search_tool(client=search_client)
    return LlmAgent(
        name=RECOMMENDER_AGENT_NAME,
        model=model,
        description="Selects the architecture pattern composition via RAG over the Pattern Catalog.",
        instruction=instruction,             # authored prompt, verbatim
        tools=[pattern_tool],                # reasoning-time retrieval tool
        output_key="recommendation",
    )


def build_orchestrator(model: str = "gemini-2.5-pro", instruction: str = "", search_client=None):
    """Build the SequentialAgent. It contains the reasoning LlmAgent plus deterministic
    BaseAgent steps that wrap the tested pipeline functions. Raises if ADK isn't available."""
    ok, reason = available()
    if not ok:
        raise RuntimeError(f"ADK orchestrator unavailable: {reason}")
    from google.adk.agents import SequentialAgent

    from .adk_steps import (
        AssembleBlueprintStep,
        ValidateSpecStep,
    )
    recommender = build_recommender_agent(model=model, instruction=instruction,
                                          search_client=search_client)
    return SequentialAgent(
        name=SEQUENTIAL_AGENT_NAME,
        description="Greenfield: validate → recommend (LLM) → assemble (deterministic, Eraser MCP tool).",
        sub_agents=[
            ValidateSpecStep(name="greenfield_validate_spec"),     # deterministic
            recommender,                                            # the ONE LLM stage
            AssembleBlueprintStep(name="greenfield_assemble_blueprint"),  # deterministic + Eraser MCP tool
        ],
    )
