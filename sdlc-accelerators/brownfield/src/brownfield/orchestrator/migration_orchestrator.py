"""Brownfield migration orchestrator — an ADK SequentialAgent exposing the four-tool pipeline.

Wraps the ALREADY-TESTED brownfield pipeline as an ADK SequentialAgent for observability, agent
identity, and Model Armor callbacks — without changing the pipeline contract. The ONE reasoning
stage is an ADK LlmAgent; substitution, ADR compliance, and assembly stay deterministic. The ADR
gate is preserved as its own step between reasoning and assembly.

Agent names (DISTINCT from greenfield):
  - SequentialAgent:    "brownfield_migration_orchestrator"
  - reasoning LlmAgent: "brownfield_pattern_recommender"
"""
from __future__ import annotations

SEQUENTIAL_AGENT_NAME = "brownfield_migration_orchestrator"
RECOMMENDER_AGENT_NAME = "brownfield_pattern_recommender"


def available() -> tuple[bool, str]:
    try:
        import google.adk.agents  # noqa: F401
    except ImportError:
        return False, "google-adk not installed (pip install google-adk)"
    return True, ""


def build_recommender_agent(model: str = "gemini-2.5-pro", instruction: str = "",
                            search_client=None):
    """Build the single brownfield reasoning sub-agent (an ADK LlmAgent). Instruction is the
    human-authored brownfield migration prompt, bound verbatim. Transition-pattern retrieval
    (Vertex AI Search) is attached as an ADK FunctionTool — the recommender decides what to query
    per integration and reasons over the candidates. search_client is injectable for tests."""
    from google.adk.agents import LlmAgent

    from .pattern_search_tool import make_transition_pattern_search_tool
    pattern_tool = make_transition_pattern_search_tool(client=search_client)
    return LlmAgent(
        name=RECOMMENDER_AGENT_NAME,
        model=model,
        description="Selects the migration transition pattern per integration via RAG over the Pattern Catalog.",
        instruction=instruction,
        tools=[pattern_tool],                # reasoning-time retrieval tool
        output_key="pattern_selection",
    )


def build_orchestrator(model: str = "gemini-2.5-pro", instruction: str = "", search_client=None):
    """Build the brownfield SequentialAgent: readiness → substitution → recommend (LLM) →
    ADR compliance → assemble (deterministic, Eraser MCP tool). Raises if ADK isn't available."""
    ok, reason = available()
    if not ok:
        raise RuntimeError(f"ADK orchestrator unavailable: {reason}")
    from google.adk.agents import SequentialAgent

    from .adk_steps import (
        AdrComplianceStep,
        AssembleContractStep,
        MigrationReadinessStep,
        SubstitutionStep,
    )
    recommender = build_recommender_agent(model=model, instruction=instruction,
                                          search_client=search_client)
    return SequentialAgent(
        name=SEQUENTIAL_AGENT_NAME,
        description="Brownfield: readiness → substitution → recommend (LLM) → ADR → assemble (deterministic).",
        sub_agents=[
            MigrationReadinessStep(name="brownfield_migration_readiness"),  # deterministic
            SubstitutionStep(name="brownfield_substitution"),               # deterministic, NO LLM
            recommender,                                                    # the ONE LLM stage
            AdrComplianceStep(name="brownfield_adr_compliance"),            # deterministic gate (preserved)
            AssembleContractStep(name="brownfield_assemble_contract"),      # deterministic + Eraser MCP tool
        ],
    )
