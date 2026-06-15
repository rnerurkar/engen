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

TEMPLATE_DIR = Path(__file__).parent  # default; overridden by main(template_dir=...)
MCP_TOOL_SUFFIXES = ("-mcp",)



def _tool_type_map(tool_bindings: list[dict]) -> dict:
    """name -> type, so templates can render the right accessor."""
    return {tb["name"]: tb["type"] for tb in tool_bindings}


def safe_fn_name(name: str) -> str:
    """Sanitize a function_tool name into a valid Python identifier."""
    s = re.sub(r"[^0-9a-zA-Z_]+", "_", name).strip("_")
    return s if s.endswith("_fn") else s + "_fn"


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


def build_env(template_dir: Path = TEMPLATE_DIR) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        trim_blocks=False,
        lstrip_blocks=False,
        keep_trailing_newline=True,
    )
    env.tests["mcp_tool"] = is_mcp_tool
    env.filters["to_class_name"] = to_class_name
    env.filters["select_function_tools"] = select_function_tools
    env.filters["group_by_implementer"] = group_by_implementer
    env.filters["render_rule_branch"] = render_rule_branch
    env.filters["safe_fn_name"] = safe_fn_name
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
    if t == "LoopAgent" and agent.get("children"):
        # LoopAgent as a NODE (wraps children). A LoopAgent used only as a retry
        # sub-field of an LlmAgent is handled inside agent_llm.py.j2 instead.
        return "agent_loop.py.j2"
    if t == "CustomAgent":
        return "agent_hitl.py.j2"
    return "agent_llm.py.j2"


def main(blueprint_path: str, out_dir: str, template_dir: str | None = None) -> None:
    blueprint = json.loads(Path(blueprint_path).read_text())
    out = Path(out_dir)
    (out / "agents").mkdir(parents=True, exist_ok=True)
    (out / "tools").mkdir(parents=True, exist_ok=True)
    (out / "callbacks").mkdir(parents=True, exist_ok=True)

    tdir = Path(template_dir) if template_dir else TEMPLATE_DIR
    env = build_env(tdir)
    screening = blueprint["screening_config"]
    tool_types = _tool_type_map(blueprint["tool_bindings"])

    # One file per agent, deterministic order
    for agent in walk_agents(blueprint["adk_agent_tree"]["root"]):
        tmpl = env.get_template(template_for(agent))
        code = tmpl.render(agent=agent, screening=screening, tool_types=tool_types)
        (out / "agents" / f"{agent['name']}.py").write_text(code)

    # FunctionTools from business rules
    ft = env.get_template("function_tools.py.j2")
    (out / "tools" / "function_tools.py").write_text(
        ft.render(business_rules=blueprint["business_rules"])
    )

    # Model Armor callbacks
    ma = env.get_template("model_armor.py.j2")
    (out / "callbacks" / "model_armor.py").write_text(ma.render(screening=screening))

    # MCP + A2A client wiring
    mcp = env.get_template("mcp_clients.py.j2")
    (out / "tools" / "mcp_clients.py").write_text(mcp.render(tool_bindings=blueprint["tool_bindings"]))
    a2a = env.get_template("a2a_clients.py.j2")
    (out / "tools" / "a2a_clients.py").write_text(a2a.render(tool_bindings=blueprint["tool_bindings"]))

    # Agent Identity
    (out / "identity").mkdir(parents=True, exist_ok=True)
    ident = env.get_template("agent_identity.py.j2")
    (out / "identity" / "agent_identity.py").write_text(
        ident.render(agent_identity_config=blueprint["agent_identity_config"])
    )

    # Terraform (Constitution Rules 4, 8-10) — company modules + per-agent SAs
    (out / "terraform").mkdir(parents=True, exist_ok=True)
    main_tf = env.get_template("terraform/main.tf.j2")
    (out / "terraform" / "main.tf").write_text(main_tf.render(
        metadata=blueprint["metadata"],
        infra_modules=blueprint.get("infra_modules", []),
    ))
    agents_tf = env.get_template("terraform/agents.tf.j2")
    (out / "terraform" / "agents.tf").write_text(agents_tf.render(
        agent_identity_config=blueprint["agent_identity_config"],
    ))

    # Entrypoint
    mn = env.get_template("main.py.j2")
    (out / "main.py").write_text(
        mn.render(metadata=blueprint["metadata"], adk_agent_tree=blueprint["adk_agent_tree"])
    )

    # Required artifacts (constitution Rules 11/13) — always generated.
    # .pre-commit-config.yaml wires lint + inner-loop eval to run on every `git commit`.
    pc = env.get_template(".pre-commit-config.yaml.j2")
    (out / ".pre-commit-config.yaml").write_text(pc.render(metadata=blueprint["metadata"]))
    ev = env.get_template("eval_inner_loop.py.j2")
    (out / "tests").mkdir(parents=True, exist_ok=True)
    (out / "tests" / "eval_inner_loop.py").write_text(ev.render(metadata=blueprint["metadata"]))

    agent_count = sum(1 for _ in walk_agents(blueprint["adk_agent_tree"]["root"]))
    print(f"Rendered {agent_count} agents + function_tools + model_armor + main "
          f"+ pre-commit hook → {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
