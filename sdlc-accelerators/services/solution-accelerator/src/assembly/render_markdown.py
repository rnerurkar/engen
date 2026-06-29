"""Render the §1-§9 app-blueprint.md (the PRIMARY governance artifact) from selections.
Deterministic, no LLM. Technical config is NOT inlined (it derives into .json) — the .md
carries the human-readable governance sections.
"""

from __future__ import annotations

from typing import Any

from .selections import AgentSelection, ArchitectureSelections


def _tree_lines(a: AgentSelection, depth: int = 0) -> list[str]:
    pad = "  " * depth
    tools = f" — tools: {', '.join(a.tools)}" if a.tools else ""
    out = [f"{pad}- **{a.name}** ({a.type}): {a.role}{tools}"]
    for c in a.children:
        out += _tree_lines(c, depth + 1)
    return out


def render_markdown(
    sel: ArchitectureSelections, component_png: str, hadr_png: str
) -> str:
    s = []
    s.append(f"# Application Blueprint — {sel.use_case}\n")
    s.append(
        f"> Solution: `{sel.solution_id}` · Archetype: {sel.archetype} · "
        f"Overall confidence: **{sel.overall_confidence}**\n"
    )

    # §1 Application Overview
    s.append("## §1. Application Overview\n")
    s.append(
        f"{sel.use_case}. Primary pattern: **{sel.primary_pattern}**. "
        f"This solution composes {len(sel.pattern_composition)} pattern(s) into an agentic "
        f"workflow of {_count_agents(sel.agent_tree)} agents.\n"
    )

    # §2 Component Topology Diagram
    s.append("## §2. Component Topology Diagram\n")
    s.append(f"![Component Topology](diagrams/{component_png})\n")
    s.append("**Agent topology:**\n")
    s += _tree_lines(sel.agent_tree)
    s.append("")

    # §3 Architecture Patterns
    s.append("## §3. Architecture Patterns\n")
    s.append("| Pattern | Role | Nesting | Confidence |")
    s.append("|---|---|---|---|")
    for p in sel.pattern_composition:
        s.append(f"| {p.pattern} | {p.role} | {p.nesting or '—'} | {p.confidence} |")
    s.append("")

    # §4 Tech Stack
    s.append("## §4. Application Tech Stack\n")
    s.append("| Layer | Choice |")
    s.append("|---|---|")
    s.append("| Agent framework | Google ADK |")
    s.append(f"| Models | {_models(sel.agent_tree) or 'gemini-2.0-flash'} |")
    s.append(
        "| Skills (with provenance) | "
        + (
            ", ".join(
                (
                    f"{sk.name} (CREATE — no catalog match)"
                    if sk.status == "to_create"
                    else f"{sk.name}@{sk.version}"
                )
                for sk in sel.skills
            )
            or "—"
        )
        + " |"
    )
    s.append("")

    # New skills & tools to create — emitted when nothing matched (A2A > MCP > Build for tools;
    # Skill Catalog for skills). The coding agent (/accelerator.generate) creates these from app-blueprint.json.
    new_skills = [sk for sk in sel.skills if sk.status == "to_create"]
    new_tools = [t for t in sel.tools if t.status == "to_create"]
    if new_skills or new_tools:
        s.append(
            "### New skills & tools to create — YOUR CODE HERE (no catalog match)\n"
        )
        for sk in new_skills:
            d = sk.definition or {}
            s.append(
                f"- **Skill `{sk.name}`** (for `{sk.assigned_to}`) — no Skill-Catalog match; "
                f"create `skills/{sk.name}/SKILL.md`. {d.get('description', '')}"
            )
        for t in new_tools:
            d = t.definition or {}
            s.append(
                f"- **FunctionTool `{t.name}`** (for `{t.assigned_to}`) — no A2A agent or MCP tool "
                f"matched; implement a new ADK FunctionTool. {d.get('description', '')}"
            )
        s.append(
            "\n> Definitions (SKILL.md + tool I/O schemas) are in `app-blueprint.json` → `to_create`.\n"
        )

    # §5 DevSecOps Stack
    s.append("## §5. DevSecOps Stack\n")
    s.append(
        f"Model Armor: {sel.screening.get('model_armor_level', 'standard')}. "
        "CI: Cloud Build. CD: Harness (downstream). Signing: cosign + Binary Authorization.\n"
    )

    # §6 HA/DR Guidance
    s.append("## §6. HA/DR Guidance\n")
    s.append(
        f"Strategy: **{sel.hadr.get('strategy', 'TBD')}**. "
        f"Primary: {sel.hadr.get('primary_region', 'TBD')} · "
        f"DR: {sel.hadr.get('dr_region', 'TBD')}.\n"
    )

    # §7 HA/DR Lifecycle Diagrams
    s.append("## §7. HA/DR Lifecycle Diagrams\n")
    s.append(f"![HA/DR Lifecycle](diagrams/{hadr_png})\n")

    # §8 Architecture Decision Log
    s.append("## §8. Architecture Decision Log\n")
    s.append("| # | Decision | Rationale |")
    s.append("|---|---|---|")
    s.append(
        f"| 1 | Primary pattern = {sel.primary_pattern} | Derived from spec ordering words |"
    )
    for i, t in enumerate(sel.tools, start=2):
        if t.type == "a2a_agent":
            s.append(
                f"| {i} | Use A2A agent {t.name} | Partner operates own system (A2A > MCP > Build) |"
            )
    s.append("")

    # §9 NFRs
    s.append("## §9. Non-Functional Requirements\n")
    s.append("| NFR | Target |")
    s.append("|---|---|")
    for k, v in (sel.nfr_targets or {}).items():
        tgt = v.get("target") if isinstance(v, dict) else v
        s.append(f"| {k} | {tgt} |")
    s.append("")

    return "\n".join(s) + "\n"


def _count_agents(a: AgentSelection) -> int:
    return 1 + sum(_count_agents(c) for c in a.children)


def _models(a: AgentSelection) -> str:
    found = set()

    def walk(n: Any) -> None:
        if n.model:
            found.add(n.model)
        for c in n.children:
            walk(c)

    walk(a)
    return ", ".join(sorted(found))
