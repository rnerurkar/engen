"""Brownfield migration orchestrator: ADK SequentialAgent, single reasoning LlmAgent, ADR gate
preserved as a deterministic step, distinct agent names from greenfield."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from brownfield.orchestrator import migration_orchestrator as mo


def test_available():
    ok, reason = mo.available()
    assert ok is True, reason


def test_orchestrator_five_stages_with_adr_gate_preserved():
    from google.adk.agents import LlmAgent, SequentialAgent

    orch = mo.build_orchestrator(instruction="BF PROMPT")
    assert isinstance(orch, SequentialAgent)
    assert orch.name == "brownfield_migration_orchestrator"
    names = [a.name for a in orch.sub_agents]
    assert names == [
        "brownfield_migration_readiness",
        "brownfield_substitution",
        "brownfield_pattern_recommender",
        "brownfield_adr_compliance",
        "brownfield_assemble_contract",
    ]
    # ADR compliance is its OWN deterministic step (not folded into the LLM)
    adr = [a for a in orch.sub_agents if a.name == "brownfield_adr_compliance"][0]
    assert not isinstance(adr, LlmAgent)


def test_exactly_one_llm_reasoning_agent():
    from google.adk.agents import LlmAgent

    orch = mo.build_orchestrator()
    llm = [a for a in orch.sub_agents if isinstance(a, LlmAgent)]
    assert len(llm) == 1
    assert llm[0].name == "brownfield_pattern_recommender"


def test_substitution_and_assembly_are_deterministic():
    from google.adk.agents import LlmAgent

    orch = mo.build_orchestrator()
    by_name = {a.name: a for a in orch.sub_agents}
    assert not isinstance(
        by_name["brownfield_substitution"], LlmAgent
    )  # no LLM in substitution
    assert not isinstance(
        by_name["brownfield_assemble_contract"], LlmAgent
    )  # no LLM in assembly


def test_names_distinct_from_greenfield():
    from reasoning import blueprint_orchestrator as bo

    gf = {bo.SEQUENTIAL_AGENT_NAME, bo.RECOMMENDER_AGENT_NAME}
    bf = {mo.SEQUENTIAL_AGENT_NAME, mo.RECOMMENDER_AGENT_NAME}
    assert gf.isdisjoint(bf)  # no shared agent names across archetypes


def test_recommender_has_transition_pattern_search_tool():
    orch = mo.build_orchestrator(instruction="X")
    rec = [a for a in orch.sub_agents if a.name == "brownfield_pattern_recommender"][0]
    assert "search_transition_patterns" in [t.name for t in rec.tools]


def test_transition_tool_wraps_vertex_and_degrades():
    from brownfield.orchestrator.pattern_search_tool import (
        make_transition_pattern_search_tool,
    )
    from clients.vertex_search import VertexSearchClient

    tool = make_transition_pattern_search_tool(
        VertexSearchClient(_search=lambda ds, q: [{"id": "t1"}])
    )
    out = tool.func("aws-sqs", ["messaging"], "refactor")
    assert out == {"patterns": [{"id": "t1"}]}
    tool2 = make_transition_pattern_search_tool(VertexSearchClient())
    assert tool2.func("aws-sqs", ["messaging"], "refactor") == {"patterns": []}


def test_brownfield_deterministic_steps_have_no_tools():
    """Governance: substitution, ADR, assembly stay tool-free sequential steps."""
    orch = mo.build_orchestrator()
    for name in (
        "brownfield_migration_readiness",
        "brownfield_substitution",
        "brownfield_adr_compliance",
        "brownfield_assemble_contract",
    ):
        step = [a for a in orch.sub_agents if a.name == name][0]
        assert not getattr(step, "tools", [])
