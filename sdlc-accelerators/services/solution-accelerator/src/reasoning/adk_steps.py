"""Deterministic ADK steps for the greenfield blueprint orchestrator (real execution, 1a).

Each step runs real logic against ctx.session.state. ValidateSpecStep parses the spec into signals
via the tested validation; AssembleBlueprintStep runs the tested deterministic assembler and CALLS
the Eraser MCP tool to render diagrams. The reasoning LlmAgent (greenfield_architecture_recommender)
sits between them and writes its ArchitectureSelections to state under "selections".

State contract:
  in:  spec_md, plan_md, selections (ArchitectureSelections from the LLM stage), _eraser_mcp (optional)
  out: validation, blueprint_md, blueprint_json, diagrams
"""
from __future__ import annotations

import os
import sys
from collections.abc import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # this service's src (sibling pkgs)

from assembly.assemble import assemble_blueprint  # noqa: E402
from reasoning.validate_spec import validate_spec  # noqa: E402


def _text_event(author: str, text: str) -> Event:
    """Wrap a status string as an ADK model Event."""
    return Event(author=author, content=types.Content(role="model", parts=[types.Part(text=text)]))


class ValidateSpecStep(BaseAgent):
    """Deterministic: run the tested validate_spec (signal extraction + structural checks)."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run validate_spec; halt the sequence if validation reports it isn't ready."""
        state = ctx.session.state
        spec_md = state.get("spec_md", "")
        validation = validate_spec(spec_md)
        ok = getattr(validation, "ok", True)
        state["validation"] = {"ok": ok, "signals": getattr(validation, "signals", None)}
        if not ok:
            state["_blocked"] = True
            yield _text_event(self.name, "validate_spec: BLOCK — halting")
            return
        yield _text_event(self.name, "validate_spec: complete")


class AssembleBlueprintStep(BaseAgent):
    """Deterministic assembly. Reads the LLM stage's ArchitectureSelections from state, runs the
    tested assemble_blueprint, and CALLS the Eraser MCP tool to render diagrams (tool use)."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run the real deterministic assembler; render diagrams via Eraser MCP if provided."""
        state = ctx.session.state
        if state.get("_blocked"):
            return
        selections = state.get("selections")
        if selections is None:
            # No LLM selections present (e.g. structure-only run); record the hand-off truthfully.
            state["blueprint_md"] = None
            yield _text_event(self.name, "assemble_blueprint: skipped (no selections in state)")
            return
        eraser = state.get("_eraser_mcp")
        assembled = assemble_blueprint(selections, state.get("spec_md", ""),
                                       state.get("plan_md", ""), eraser_mcp=eraser)
        state["blueprint_md"] = assembled.markdown
        state["blueprint_json"] = assembled.json
        state["diagrams"] = assembled.diagrams
        yield _text_event(self.name,
                          "assemble_blueprint: complete (deterministic; Eraser MCP tool for diagrams)")
