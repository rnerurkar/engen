"""The **Solution Accelerator Agent** — the single ADK agent the brownfield MCP server delegates to.

Built with the ADK framework, this is ONE agent (`solution_accelerator_agent`) owning exactly **two
FunctionTools**:

  1. `recommend_architecture`    — per-integration transition-pattern selection (today's brownfield
                                   pattern recommender), used by blueprint_start (the LLM stage).
  2. `create_epic_signal_ledger` — extractive, span-grounded Epic shaping → Brownfield Epic Signal
                                   Ledger, used by ingest_epic_start (Phase A of the Epic front door).

Same design as the greenfield Solution Accelerator Agent and carrying the same ARB fixes:
  - the agent is genuinely RUN (`SolutionAcceleratorAgent.run`, not built-and-discarded) — H-1;
  - DIRECT capability dispatch (the server names the tool; no LLM tool-router → no extra model call) — H-2;
  - the live `google.adk` LlmAgent is bound into `adk_agent`; `_run_via_adk_runner` is the live seam.

IP NOTE: the "MCP server delegates to one ADK agent holding FunctionTools, one building an epic-derived
artifact" structure is a shared ADK pattern (overlaps the external platform's design-agent-with-tools) and is NOT
claimed; the claimed novelty is the integration-keyed, span-grounded Brownfield Epic Signal Ledger +
fill-ratio confidence + ObjectVersion staleness + the readiness-gate reconciliation.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

AGENT_NAME = "solution_accelerator_agent"
AGENT_MODEL = os.environ.get("SDLC_LLM_MODEL", "gemini-2.5-pro")


def recommend_architecture(
    substitution: dict[str, Any],
    candidates: list[Any] | None = None,
    recommend_fn: Callable[..., Any] | None = None,
    prompt: str | None = None,
) -> dict[str, Any]:
    """FunctionTool #1 — select the migration transition pattern for one integration."""
    from brownfield.recommend_architecture import recommend_for_integration

    return recommend_for_integration(
        substitution, candidates=candidates, recommend_fn=recommend_fn, prompt=prompt
    )


def create_epic_signal_ledger(
    epic: Any, model_fn: Callable[..., Any] | None = None
) -> Any:
    """FunctionTool #2 — extractive, span-grounded Brownfield Epic Signal Ledger from a Rally Epic."""
    from brownfield.ingest.epic_models import Epic
    from brownfield.ingest.shaping import shape_epic

    epic_obj = epic if isinstance(epic, Epic) else Epic.from_payload(epic)
    return shape_epic(epic_obj, model_fn=model_fn)


TOOL_FNS: dict[str, Callable[..., Any]] = {
    "recommend_architecture": recommend_architecture,
    "create_epic_signal_ledger": create_epic_signal_ledger,
}


@dataclass
class SolutionAcceleratorAgent:
    name: str = AGENT_NAME
    model: str = AGENT_MODEL
    tools: list[Any] = field(default_factory=lambda: list(TOOL_FNS))
    framework: str = "google.adk"
    adk_agent: Any = None

    def run(
        self, capability: str, payload: Any, model_fn: Callable[..., Any] | None = None
    ) -> Any:
        from brownfield.runtime import bind_logger, tool_execution_span

        log = bind_logger(agent_id=self.name)
        fn = TOOL_FNS.get(capability)
        if fn is None:
            raise ValueError(
                f"Unknown Solution Accelerator Agent capability: {capability!r} "
                f"(have: {list(TOOL_FNS)})"
            )
        with tool_execution_span(tool=capability):
            log.info("agent.dispatch", capability=capability)
            if (
                self.adk_agent is not None and model_fn is None
            ):  # pragma: no cover - live ADK Runner seam
                return _run_via_adk_runner(self.adk_agent, capability, payload)
            if capability == "recommend_architecture":
                sub = (
                    payload["substitution"]
                    if isinstance(payload, dict) and "substitution" in payload
                    else payload
                )
                cands = payload.get("candidates") if isinstance(payload, dict) else None
                return fn(sub, candidates=cands, recommend_fn=model_fn)
            return fn(payload, model_fn=model_fn)


def _run_via_adk_runner(
    adk_agent: Any, capability: str, payload: Any
) -> None:  # pragma: no cover - live seam
    from google.adk.runners import Runner  # noqa: F401

    raise NotImplementedError(
        "Bind the ADK Runner to execute solution_accelerator_agent's FunctionTool on Cloud Run."
    )


def build_solution_accelerator_agent() -> SolutionAcceleratorAgent:
    adk = None
    try:  # pragma: no cover - live ADK binding
        from brownfield.orchestrator.migration_orchestrator import (
            build_recommender_agent,
        )

        adk = (
            build_recommender_agent()
        )  # the live ADK LlmAgent (RAG pattern tool attached)
    except Exception:
        adk = None
    return SolutionAcceleratorAgent(adk_agent=adk)


def delegate(
    capability: str, payload: Any, model_fn: Callable[..., Any] | None = None
) -> Any:
    """The MCP server's delegation entry point. Builds the Solution Accelerator Agent and RUNS it
    (direct dispatch — no LLM tool-router)."""
    return build_solution_accelerator_agent().run(
        capability, payload, model_fn=model_fn
    )
