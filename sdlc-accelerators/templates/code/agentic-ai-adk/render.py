"""Reference renderer for the agentic-ai-adk domain skill.

This is the validatable proof that the domain skill + Jinja2 templates produce
code from app-blueprint.json. In the real platform this logic lives inside
accelerator-cli; here it is a standalone reference so the Phase 4 authoring can
be validated against examples/fnol/ before the CLI exists.

Usage:
    python render.py ../../examples/fnol/outputs/app-blueprint.json ./out
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent
MCP_TOOL_SUFFIXES = ("-mcp",)


def is_mcp_tool(name: str) -> bool:
    return name.endswith(MCP_TOOL_SUFFIXES)


def to_class_name(name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[_\-]", name))


def select_function_tools(tools: list[str]) -> list[str]:
    # FunctionTools are the non-mcp, non-a2a tool names (end with _fn)
    return [t for t in tools if t.endswith("_fn")]


def _sanitize_fn_name(raw: str) -> str:
    """Turn an implemented_by value into a valid Python identifier.
    Some business rules describe the implementer in prose (e.g.
    'severity_classifier (A2A delegation ...)'); collapse to the leading token.
    """
    # Take text before the first parenthesis, strip, snake-case it.
    base = raw.split("(")[0].strip()
    base = re.sub(r"[^0-9a-zA-Z_]+", "_", base).strip("_")
    if not base.endswith("_fn"):
        base = base + "_fn"
    return base


def group_by_implementer(rules: list[dict]) -> list[tuple[str, list[dict]]]:
    groups: dict[str, list[dict]] = {}
    for rule in rules:
        fn = _sanitize_fn_name(rule["implemented_by"])
        groups.setdefault(fn, []).append(rule)
    return sorted(groups.items())


def render_rule_branch(rule: dict) -> str:
    # Scaffolds an IF/THEN branch from the rule text. Human verifies the predicate.
    return f'    # TODO verify predicate for {rule["id"]}\n    # {rule["rule"]}'


def build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )
    env.tests["mcp_tool"] = is_mcp_tool
    env.filters["to_class_name"] = to_class_name
    env.filters["select_function_tools"] = select_function_tools
    env.filters["group_by_implementer"] = group_by_implementer
    env.filters["render_rule_branch"] = render_rule_branch
    return env


def walk_agents(node: dict):
    """Yield every agent node in the tree (depth-first, stable order)."""
    yield node
    for child in node.get("children", []):
        yield from walk_agents(child)


def template_for(agent: dict) -> str:
    t = agent["type"]
    if t == "SequentialAgent":
        return "agent_sequential.py.j2"
    if t == "ParallelAgent":
        return "agent_parallel.py.j2"
    if t == "CustomAgent":
        return "agent_hitl.py.j2"
    return "agent_llm.py.j2"


def main(blueprint_path: str, out_dir: str) -> None:
    blueprint = json.loads(Path(blueprint_path).read_text())
    out = Path(out_dir)
    (out / "agents").mkdir(parents=True, exist_ok=True)
    (out / "tools").mkdir(parents=True, exist_ok=True)
    (out / "callbacks").mkdir(parents=True, exist_ok=True)

    env = build_env()
    screening = blueprint["screening_config"]

    # One file per agent, deterministic order
    for agent in walk_agents(blueprint["adk_agent_tree"]["root"]):
        tmpl = env.get_template(template_for(agent))
        code = tmpl.render(agent=agent, screening=screening)
        (out / "agents" / f"{agent['name']}.py").write_text(code)

    # FunctionTools from business rules
    ft = env.get_template("function_tools.py.j2")
    (out / "tools" / "function_tools.py").write_text(
        ft.render(business_rules=blueprint["business_rules"])
    )

    # Model Armor callbacks
    ma = env.get_template("model_armor.py.j2")
    (out / "callbacks" / "model_armor.py").write_text(ma.render(screening=screening))

    # Entrypoint
    mn = env.get_template("main.py.j2")
    (out / "main.py").write_text(
        mn.render(metadata=blueprint["metadata"], adk_agent_tree=blueprint["adk_agent_tree"])
    )

    agent_count = sum(1 for _ in walk_agents(blueprint["adk_agent_tree"]["root"]))
    print(f"Rendered {agent_count} agents + function_tools + model_armor + main → {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
