"""Greenfield blueprint orchestrator: ADK SequentialAgent structure, single reasoning LlmAgent,
distinct agent names, deterministic stages."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from reasoning import blueprint_orchestrator as bo


def test_available():
    ok, reason = bo.available()
    assert ok is True, reason


def test_orchestrator_is_sequential_with_three_stages():
    from google.adk.agents import LlmAgent, SequentialAgent
    orch = bo.build_orchestrator(instruction="AUTHORED")
    assert isinstance(orch, SequentialAgent)
    assert orch.name == "greenfield_blueprint_orchestrator"
    names = [a.name for a in orch.sub_agents]
    assert names == ["greenfield_validate_spec", "greenfield_architecture_recommender",
                     "greenfield_assemble_blueprint"]
    # exactly ONE LlmAgent (the reasoning stage)
    llm_agents = [a for a in orch.sub_agents if isinstance(a, LlmAgent)]
    assert len(llm_agents) == 1
    assert llm_agents[0].name == "greenfield_architecture_recommender"


def test_recommender_binds_prompt_verbatim():
    agent = bo.build_recommender_agent(instruction="THE AUTHORED PROMPT")
    assert agent.instruction == "THE AUTHORED PROMPT"
    assert agent.name == "greenfield_architecture_recommender"


def test_deterministic_steps_are_not_llm_agents():
    from google.adk.agents import LlmAgent
    orch = bo.build_orchestrator()
    validate, _, assemble = orch.sub_agents
    assert not isinstance(validate, LlmAgent)
    assert not isinstance(assemble, LlmAgent)


def test_recommender_has_pattern_search_tool():
    from clients.vertex_search import VertexSearchClient
    orch = bo.build_orchestrator(instruction="X",
                                 search_client=VertexSearchClient(_search=lambda ds, q: []))
    recommender = orch.sub_agents[1]
    tool_names = [t.name for t in recommender.tools]
    assert "search_architecture_patterns" in tool_names


def test_pattern_search_tool_wraps_vertex_and_degrades():
    from clients.vertex_search import VertexSearchClient
    from reasoning.pattern_search_tool import make_pattern_search_tool
    # injected client returns candidates
    tool = make_pattern_search_tool(VertexSearchClient(_search=lambda ds, q: [{"id": "p1"}]))
    assert tool.func(["first", "then"]) == {"patterns": [{"id": "p1"}]}
    # unconfigured client degrades to empty (no crash)
    tool2 = make_pattern_search_tool(VertexSearchClient())
    assert tool2.func(["x"]) == {"patterns": []}


def test_deterministic_steps_have_no_tools():
    """Governance guarantee: only the recommender gets tools; gating/transform steps do not."""
    orch = bo.build_orchestrator()
    validate, _, assemble = orch.sub_agents
    assert not getattr(validate, "tools", [])
    assert not getattr(assemble, "tools", [])
