"""Tool 4 — assemble_blueprint: deterministically build the TSA blueprint + design contract v2.0.

Builds app-blueprint.md (one block per integration: pattern + substitution + IaC + attested ADRs),
the design_contract.json (v2.0, lifecycle LIVE), and the four diagram DSLs (Component end-state,
Sequence end-state, Sequence transition, Infrastructure). Injects a Phase-0 cross-cloud
coordination entry when a selected pattern uses cross-cloud topology.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

CROSS_CLOUD_TOKENS = {"privatelink", "psc", "direct-connect", "interconnect"}


@dataclass
class AssembledBrownfieldBlueprint:
    markdown: str
    design_contract: dict
    diagrams: list = field(default_factory=list)   # [{name, dsl}]


def _phase_blocks(substitutions, plan_by_id):
    """Group integrations into migration phases from the plan, with coexistence + cross-cloud flags."""
    phases = {}
    for s in substitutions:
        d = plan_by_id.get(s["integration_id"])
        phase = d.phase if d else 2
        cross = any(t in CROSS_CLOUD_TOKENS for t in s["target_tokens"])
        phases.setdefault(phase, {"integration_ids": [], "cross_cloud": False, "coexistence": "none"})
        phases[phase]["integration_ids"].append(s["integration_id"])
        if cross:
            phases[phase]["cross_cloud"] = True
        if d and d.coexistence_window and d.coexistence_window.lower() not in ("n/a", ""):
            phases[phase]["coexistence"] = (
                "dual-write" if "dual" in d.coexistence_window.lower() else "dual-read")
    return phases


def assemble_blueprint(spec, substitutions, pattern_selections, attested_adrs,
                       plan_decisions, readiness_score=100) -> AssembledBrownfieldBlueprint:
    """Deterministically build the TSA blueprint markdown, the design contract v2.0, and the four
    diagram DSLs (component/sequence-end/sequence-transition/infrastructure). Injects a Phase-0
    cross-cloud coordination entry when a selected target uses cross-cloud topology."""
    plan_by_id = {d.integration_id: d for d in plan_decisions}
    sub_by_id = {s["integration_id"]: s for s in substitutions}
    sel_by_id = {p["integration_id"]: p for p in pattern_selections}

    # --- markdown: one block per integration ---
    lines = ["# Brownfield Migration Blueprint (TSA)\n",
             f"**Migration readiness score:** {readiness_score}/100\n",
             "## Integration Migration Blocks\n"]
    for it in spec.integrations:
        iid = it.integration_id
        s = sub_by_id.get(iid, {})
        sel = sel_by_id.get(iid, {})
        adrs = [a["adr_id"] for a in attested_adrs if a["integration_id"] == iid]
        d = plan_by_id.get(iid)
        lines.append(f"### {iid} — {it.name}")
        lines.append(f"- R-factor: {d.r_factor if d else '?'}")
        lines.append(f"- Substitution: {s.get('source_tokens', [])} → {s.get('target_tokens', [])}")
        lines.append(f"- Pattern: {sel.get('pattern_ref', 'n/a')} (confidence {sel.get('confidence', 0)})")
        cutover = d.cutover_strategy if d else '?'
        lines.append(f"- Transition: {s.get('transition_pattern_ref', 'n/a')}; cutover {cutover}")
        lines.append(f"- Attested ADRs: {', '.join(adrs) if adrs else 'none'}")
        lines.append(f"- Rollback: {d.rollback_path if d else 'UNSPECIFIED'}\n")

    # --- migration phases (+ cross-cloud Phase-0 injection) ---
    phases = _phase_blocks(substitutions, plan_by_id)
    migration_phases = []
    if any(p["cross_cloud"] for p in phases.values()):
        migration_phases.append({
            "phase": 0, "name": "Cross-cloud plumbing (external-team coordination)",
            "integration_ids": [s["integration_id"] for s in substitutions
                                if any(t in CROSS_CLOUD_TOKENS for t in s["target_tokens"])],
            "coexistence": "none", "cross_cloud_coordination": True,
        })
    for ph in sorted(phases):
        migration_phases.append({
            "phase": ph, "name": f"Phase {ph}",
            "integration_ids": phases[ph]["integration_ids"],
            "coexistence": phases[ph]["coexistence"],
            "cross_cloud_coordination": phases[ph]["cross_cloud"],
        })

    # --- design contract v2.0 ---
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    contract = {
        "schema_version": "2.0", "lifecycle": "LIVE",
        "generated_at": now, "last_refreshed_at": now,
        "migration_readiness_score": readiness_score,
        "tech_substitutions": substitutions,
        "pattern_selections": pattern_selections,
        "attested_adrs": attested_adrs,
        "migration_phases": migration_phases,
        "cutover_strategy": "; ".join(
            f"{d.integration_id}:{d.cutover_strategy}" for d in plan_decisions),
        "staleness_triggers": {
            "adr_store_version": "v1", "substitution_table_version": "v1", "iac_manifest_version": "v1",
        },
    }

    # --- four diagram DSLs (deterministic; rendered by the Eraser MCP server downstream) ---
    diagrams = [
        {"name": "component-end-state", "dsl": _component_dsl(substitutions, pattern_selections)},
        {"name": "sequence-end-state", "dsl": _sequence_end_dsl(spec)},
        {"name": "sequence-transition", "dsl": _sequence_transition_dsl(migration_phases, plan_by_id)},
        {"name": "infrastructure", "dsl": _infra_dsl(substitutions)},
    ]
    return AssembledBrownfieldBlueprint(markdown="\n".join(lines), design_contract=contract, diagrams=diagrams)


def _component_dsl(subs, sels):
    """Build the end-state component-diagram DSL (one node per integration target)."""
    rows = ["// Component (end-state TSA)"]
    for s in subs:
        rows.append(f'{s["integration_id"]} [label: "{"+".join(s["target_tokens"])}"]')
    return "\n".join(rows)


def _sequence_end_dsl(spec):
    """Build the end-state runtime sequence DSL."""
    rows = ["// Sequence (end-state)"]
    for it in spec.integrations:
        rows.append(f'Client -> {it.integration_id}: {it.name}')
    return "\n".join(rows)


def _sequence_transition_dsl(phases, plan_by_id):
    """Build the transition sequence DSL (dual-write windows, strangler routes, cutover gates)."""
    rows = ["// Sequence (transition: dual-write windows, strangler routes, cutover gates)"]
    for ph in phases:
        for iid in ph["integration_ids"]:
            d = plan_by_id.get(iid)
            win = d.coexistence_window if d else ""
            suffix = ("(" + win + ")") if win else ""
            rows.append(f'Phase{ph["phase"]} -> {iid}: {d.cutover_strategy if d else ""} {suffix}')
    return "\n".join(rows)


def _infra_dsl(subs):
    """Build the infrastructure DSL (cross-cloud links where targets require them)."""
    rows = ["// Infrastructure (AWS account, VPC, region, cross-cloud links)"]
    for s in subs:
        cc = [t for t in s["target_tokens"] if t in CROSS_CLOUD_TOKENS]
        if cc:
            rows.append(f'{s["integration_id"]}: cross-cloud link ({"+".join(cc)})')
    return "\n".join(rows)
