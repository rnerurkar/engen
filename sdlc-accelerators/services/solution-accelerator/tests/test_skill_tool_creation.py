"""Verify the no-match → create-new behavior (A2A > MCP > Build for tools; Skill Catalog for skills).

When recommend_architecture finds no Skill-Catalog match, it emits a to_create SKILL.md definition;
when no A2A agent and no MCP tool match, it emits a to_create function_tool definition. The deterministic
assembly surfaces both in app-blueprint.json -> to_create so the coding agent creates them.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from assembly.derive_json import derive_json  # noqa: E402
from assembly.render_markdown import render_markdown  # noqa: E402
from assembly.selections import (  # noqa: E402
    AgentSelection,
    ArchitectureSelections,
    PatternSelection,
    SkillSelection,
    ToolSelection,
)


def _sel():
    root = AgentSelection(
        name="root",
        type="LlmAgent",
        role="coordinator",
        tools=["policy-mcp", "vin_lookup"],
    )
    return ArchitectureSelections(
        solution_id="demo",
        use_case="demo",
        archetype="agentic",
        primary_pattern="LlmAgent",
        pattern_composition=[
            PatternSelection(pattern="LlmAgent", role="root", confidence="high")
        ],
        agent_tree=root,
        tools=[
            # matched MCP tool (exists in API Hub)
            ToolSelection(
                name="policy-mcp",
                type="mcp_server",
                assigned_to="root",
                endpoint="mcp://policy",
                discovered_via="Apigee API Hub",
                status="matched",
            ),
            # NO A2A and NO MCP match → build a new FunctionTool
            ToolSelection(
                name="vin_lookup",
                type="function_tool",
                assigned_to="root",
                discovered_via="none (to_create)",
                status="to_create",
                definition={
                    "description": "Look up a vehicle by VIN",
                    "input_schema": {"vin": "string"},
                    "output_schema": {
                        "make": "string",
                        "model": "string",
                        "year": "int",
                    },
                    "rationale": "No A2A agent or MCP tool exposes VIN lookup",
                },
            ),
        ],
        skills=[
            SkillSelection(
                name="alloydb-access",
                assigned_to="root",
                sha="abc123",
                version="2.1.0",
                status="matched",
            ),
            # NO catalog match → write a new SKILL.md
            SkillSelection(
                name="fnol-severity-rubric",
                assigned_to="root",
                status="to_create",
                definition={
                    "description": "Score claim severity for FNOL intake",
                    "skill_md": "---\nname: fnol-severity-rubric\n"
                    "description: Score claim severity\n---\n"
                    "# FNOL Severity Rubric\nClassify each claim ...",
                },
            ),
        ],
        business_rules=[],
    )


def test_to_create_skill_and_tool_in_json():
    j = derive_json(_sel(), "spec", "plan", "blueprint")
    tc = j["to_create"]
    skill_names = [s["name"] for s in tc["skills"]]
    tool_names = [t["name"] for t in tc["function_tools"]]
    assert skill_names == ["fnol-severity-rubric"], (
        "unmatched skill must be in to_create.skills"
    )
    assert tool_names == ["vin_lookup"], (
        "unmatched tool must be in to_create.function_tools"
    )
    assert (
        "SKILL.md" not in tc["skills"][0]["definition"]
    )  # sanity (it's the content, key is skill_md)
    assert tc["skills"][0]["definition"]["skill_md"].startswith("---"), (
        "SKILL.md content emitted"
    )
    assert tc["function_tools"][0]["definition"]["input_schema"] == {"vin": "string"}
    # matched items keep provenance / binding info and are NOT in to_create
    sk = {s["name"]: s for s in j["skills"]}
    assert (
        sk["alloydb-access"]["status"] == "matched"
        and sk["alloydb-access"]["sha"] == "abc123"
    )
    assert sk["fnol-severity-rubric"]["status"] == "to_create"
    tb = {t["name"]: t for t in j["tool_bindings"]}
    assert (
        tb["policy-mcp"]["status"] == "matched" and "definition" not in tb["policy-mcp"]
    )
    assert (
        tb["vin_lookup"]["status"] == "to_create"
        and tb["vin_lookup"]["definition"]["rationale"]
    )


def test_markdown_flags_creation():
    md = render_markdown(_sel(), "component.png", "hadr.png")
    assert "New skills & tools to create" in md
    assert "fnol-severity-rubric" in md and "no catalog match" in md.lower()
    assert "vin_lookup" in md and "FunctionTool" in md


if __name__ == "__main__":
    test_to_create_skill_and_tool_in_json()
    test_markdown_flags_creation()
    print(
        "OK — skill/tool to_create behavior verified (A2A > MCP > Build; Skill Catalog → SKILL.md)"
    )
