"""Deterministic ADK steps for the brownfield migration orchestrator (real execution, 1a).

Each step ACTUALLY runs the corresponding tested pipeline function, reading inputs from and writing
results to ctx.session.state. The ADR compliance gate is preserved as its own deterministic step
between reasoning and assembly. Assembly is deterministic and only CALLS the Eraser MCP tool to
render diagrams.

State contract (keys in ctx.session.state):
  in:  spec_md, plan_md, substitution_rows, adr_rules, _eraser_mcp (optional), recommendation
  out: spec, plan, readiness, substitutions, attested_adrs, blueprint_md, design_contract, diagrams
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from ..adr_compliance_check import adr_compliance_check
from ..assemble_blueprint import assemble_blueprint
from ..map_current_to_target import SubstitutionRow, map_current_to_target
from ..plan_parser import parse_plan
from ..spec_parser import parse_spec
from ..validate_spec import BLOCK, validate_spec


def _text_event(author: str, text: str) -> Event:
    """Wrap a status string as an ADK model Event."""
    return Event(author=author, content=types.Content(role="model", parts=[types.Part(text=text)]))


class MigrationReadinessStep(BaseAgent):
    """Deterministic: parse spec/plan and run the 8-signal validate_spec migration-readiness gate."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run validate_spec; halt the sequence on BLOCK."""
        state = ctx.session.state
        spec = parse_spec(state.get("spec_md", ""))
        plan = parse_plan(state.get("plan_md", ""))
        state["spec"] = spec
        state["plan"] = plan
        report = validate_spec(spec)
        state["readiness"] = {"score": report.score, "overall": report.overall,
                              "phases": report.phase_assignment_preview}
        if report.overall == BLOCK:
            state["_blocked"] = True
            yield _text_event(self.name, f"migration_readiness: BLOCK (score {report.score}) — halting")
            return
        yield _text_event(self.name, f"migration_readiness: {report.overall} (score {report.score})")


class SubstitutionStep(BaseAgent):
    """Deterministic: map_current_to_target (context-filtered decision table; NO LLM)."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run the deterministic substitution; record tech_substitutions in state."""
        state = ctx.session.state
        if state.get("_blocked"):
            return
        spec = state["spec"]
        plan_by_id = {d.integration_id: d for d in state["plan"]}
        rows = [r if isinstance(r, SubstitutionRow) else SubstitutionRow(**r)
                for r in state.get("substitution_rows", [])]
        integrations = [{"integration_id": it.integration_id,
                         "source_tech": it.get("technology + version"),
                         "r_factor": plan_by_id[it.integration_id].r_factor,
                         "context": plan_by_id[it.integration_id].context}
                        for it in spec.integrations]
        result = map_current_to_target(integrations, rows)
        state["substitutions"] = result["tech_substitutions"]
        yield _text_event(self.name,
                          f"map_current_to_target: {len(state['substitutions'])} substitutions (deterministic)")


class AdrComplianceStep(BaseAgent):
    """Deterministic: adr_compliance_check (predicate DSL; NO LLM). A SEPARATE gate."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run ADR compliance per integration; record attested_adrs in state."""
        state = ctx.session.state
        if state.get("_blocked"):
            return
        adr_rules = state.get("adr_rules", [])
        attested = []
        for s in state.get("substitutions", []):
            key = {"source_tech": (s["source_tokens"] or [""])[0],
                   "target_tech": (s["target_tokens"] or [""])[0],
                   "functional_category": "", "r_factor": s["r_factor"]}
            res = adr_compliance_check(s["integration_id"], key, dict(s.get("context_matched", {})), adr_rules)
            attested.extend(res.attested_adrs)
        state["attested_adrs"] = attested
        yield _text_event(self.name, "adr_compliance_check: complete (deterministic predicate DSL)")


class AssembleContractStep(BaseAgent):
    """Deterministic: assemble_blueprint + design contract v2.0. Reads the recommendation produced
    by the LLM stage; CALLS the Eraser MCP tool to render diagram DSLs (tool use, not LLM authorship)."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run deterministic assembly; render diagrams via the Eraser MCP tool if provided."""
        state = ctx.session.state
        if state.get("_blocked"):
            return
        spec = state["spec"]
        plan = state["plan"]
        substitutions = state.get("substitutions", [])
        # The reasoning stage writes per-integration selections under "recommendation"; fall back to
        # the substitution's transition ref if the LLM stage was not run (e.g. structure-only runs).
        recommendation = state.get("recommendation") or {}
        pattern_selections = []
        for s in substitutions:
            sel = recommendation.get(s["integration_id"], {}) if isinstance(recommendation, dict) else {}
            pattern_selections.append({"integration_id": s["integration_id"],
                                       "pattern_ref": sel.get("pattern_ref", s.get("transition_pattern_ref", "n/a")),
                                       "confidence": sel.get("confidence", 0.0)})
        assembled = assemble_blueprint(spec, substitutions, pattern_selections,
                                       state.get("attested_adrs", []), plan,
                                       state.get("readiness", {}).get("score", 100))
        diagrams = assembled.diagrams
        eraser = state.get("_eraser_mcp")
        if eraser is not None:
            # tool use: render each DSL -> {drawio_xml, png_base64} (deterministic, no LLM)
            for d in diagrams:
                rendered = eraser.render(d["dsl"]) if hasattr(eraser, "render") else None
                if rendered is not None:
                    d["drawio_xml"] = getattr(rendered, "drawio_xml", "")
                    d["png_base64"] = getattr(rendered, "png_base64", "")
        state["blueprint_md"] = assembled.markdown
        state["design_contract"] = assembled.design_contract
        state["diagrams"] = diagrams
        yield _text_event(self.name,
                          "assemble_blueprint: complete (deterministic; Eraser MCP tool for diagrams)")
