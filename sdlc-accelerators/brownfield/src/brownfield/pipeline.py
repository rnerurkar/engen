"""Brownfield pipeline — chains the four tools: validate_spec -> map_current_to_target ->
recommend_architecture -> adr_compliance_check -> assemble_blueprint.

recommend_architecture is the only LLM stage (injected as recommend_fn for tests / wired to the
RAG + LlmAgent seam in production). The other stages are deterministic.
"""

from __future__ import annotations

from typing import Any

from .adr_compliance_check import adr_compliance_check
from .assemble_blueprint import assemble_blueprint
from .map_current_to_target import map_current_to_target
from .plan_parser import parse_plan
from .spec_parser import parse_spec
from .validate_spec import BLOCK, validate_spec


class MigrationReadinessBlocked(Exception):
    def __init__(self, report: Any) -> None:
        self.report = report
        blockers = [
            f"{ir.integration_id}:{s.signal}"
            for ir in report.per_integration
            for s in ir.signals
            if s.status == BLOCK
        ]
        super().__init__(
            f"Migration readiness BLOCK (score {report.score}): {blockers}"
        )


def run_brownfield_pipeline(
    spec_md: str,
    plan_md: str,
    substitution_rows: list[Any],
    adr_rules: list[Any],
    recommend_fn: Any = None,
    pattern_candidates: Any = None,
) -> dict[str, Any]:
    """Run the full brownfield pipeline. Returns {blueprint_md, design_contract, diagrams,
    readiness}. recommend_fn(integration, substitution) -> {pattern_ref, confidence, ...};
    if None, pattern selection degrades to a deterministic placeholder (live LLM is the seam)."""
    spec = parse_spec(spec_md)
    plan = parse_plan(plan_md)
    plan_by_id = {d.integration_id: d for d in plan}

    # Step 0: 8-signal readiness gate
    readiness = validate_spec(spec)
    if readiness.overall == BLOCK:
        raise MigrationReadinessBlocked(readiness)

    # Tool 1: deterministic substitution
    integrations = [
        {
            "integration_id": it.integration_id,
            "source_tech": it.get("technology + version"),
            "r_factor": plan_by_id[it.integration_id].r_factor,
            "context": plan_by_id[it.integration_id].context,
        }
        for it in spec.integrations
    ]
    sub_result = map_current_to_target(integrations, substitution_rows)
    substitutions = sub_result["tech_substitutions"]

    # Tool 2: recommend_architecture (the one LLM reasoning stage; live provider or injected fn)
    from .recommend_architecture import recommend_for_integration

    pattern_selections = []
    for s in substitutions:
        sel = recommend_for_integration(
            s, candidates=pattern_candidates, recommend_fn=recommend_fn
        )
        pattern_selections.append({"integration_id": s["integration_id"], **sel})

    # Tool 3: deterministic ADR compliance
    attested_adrs = []
    for s in substitutions:
        key = {
            "source_tech": (s["source_tokens"] or [""])[0],
            "target_tech": (s["target_tokens"] or [""])[0],
            "functional_category": "",
            "r_factor": s["r_factor"],
        }
        ctx = dict(s.get("context_matched", {}))
        res = adr_compliance_check(s["integration_id"], key, ctx, adr_rules)
        attested_adrs.extend(res.attested_adrs)

    # Tool 4: assemble
    assembled = assemble_blueprint(
        spec, substitutions, pattern_selections, attested_adrs, plan, readiness.score
    )
    return {
        "blueprint_md": assembled.markdown,
        "design_contract": assembled.design_contract,
        "diagrams": assembled.diagrams,
        "readiness": {
            "score": readiness.score,
            "overall": readiness.overall,
            "phases": readiness.phase_assignment_preview,
        },
    }
