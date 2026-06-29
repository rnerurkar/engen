"""The **Solution Accelerator Agent** — the single ADK agent the MCP server delegates to.

Built with the **ADK framework** (`google.adk`), this is ONE `LlmAgent` named `solution_accelerator_agent`
that owns exactly **two FunctionTools**:

  1. `recommend_architecture`     — RAG-grounded architecture reasoning → ArchitectureSelections
                                     (used by blueprint_start, full-lifecycle Step 5).
  2. `create_epic_signal_ledger`  — extractive Epic shaping → Epic Signal Ledger
                                     (used by ingest_epic_start, Phase A of the Greenfield front door).

Delegation model: the Solution Accelerator MCP Server does NOT reason itself. Its async tool handlers
(`blueprint_start`, `ingest_epic_start`) hand the task to THIS agent; the agent carries the two
FunctionTools and runs the model (Gemini). The MCP tools exposed to the IDE are unchanged — these two are
INTERNAL FunctionTools of the agent, never surfaced to the coding agent.

Live seam: when `google.adk` is installed the real `LlmAgent` + `FunctionTool`s are constructed and run
via the ADK Runner. Without the SDK (this environment), `build_solution_accelerator_agent()` returns a
faithful descriptor and `delegate()` invokes the tool callables directly, so the pipeline stays runnable
and testable. Either way the model call inside each tool flows through reasoning.llm_harness.invoke_llm_agent
(inject `model_fn` in tests; live Gemini otherwise).

IP NOTE: the "one ADK agent that an MCP server delegates to, holding FunctionTools (one of which builds an
epic-derived intermediate artifact)" is a SHARED ADK architectural pattern — it overlaps with the external platform's
design-agent-with-tools structure and is therefore NOT relied on as a distinguishing claim for SDLC
Accelerators. What IS distinctive (and claimed) lives in the artifact + mechanism: the section-keyed,
span-traced Epic Signal Ledger, the extractive "cannot invent" guarantee, deterministic fill-ratio
confidence, Rally ObjectVersion staleness token, and the assess-gate Epic-coverage finding.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

AGENT_NAME = "solution_accelerator_agent"
AGENT_MODEL = os.environ.get("SDLC_LLM_MODEL", "gemini-2.5-pro")


# ---- The two FunctionTools (the agent's only capabilities) -----------------------------------------


def recommend_architecture(
    spec: str, plan: str, model_fn: Callable[..., Any] | None = None
) -> Any:
    """FunctionTool #1. Produce a validated ArchitectureSelections from spec.md + plan.md
    (validate_spec → RAG/API-Hub retrieve → reason → parse). Used by blueprint_start (Step 5)."""
    from reasoning.recommend_architecture import RecommendArchitecture

    return RecommendArchitecture().run(spec, plan, model_fn=model_fn)


def create_epic_signal_ledger(
    epic: Any, model_fn: Callable[..., Any] | None = None
) -> Any:
    """FunctionTool #2. Produce the section-keyed, span-traced Epic Signal Ledger from a Rally Epic
    (extractive shaping; the deterministic validator drops any signal not verbatim in the Epic).
    Used by ingest_epic_start (Phase A). Accepts an Epic or a raw epic payload dict."""
    from ingest.epic_models import Epic
    from ingest.shaping import shape_epic

    epic_obj = epic if isinstance(epic, Epic) else Epic.from_payload(epic)
    return shape_epic(epic_obj, model_fn=model_fn)


# Tool registry — the two FunctionTools by name (what the agent is configured with).
TOOL_FNS: dict[str, Callable[..., Any]] = {
    "recommend_architecture": recommend_architecture,
    "create_epic_signal_ledger": create_epic_signal_ledger,
}


@dataclass
class SolutionAcceleratorAgent:
    """The Solution Accelerator Agent as a runnable unit. Carries the agent identity, the two
    FunctionTools, and (when google.adk is importable) the bound live `LlmAgent` in `adk_agent`.

    Dispatch model (H-2): the MCP server NAMES the capability it needs, and the agent runs that
    FunctionTool directly. There is **no LLM tool-router** — we do NOT spend a model call to decide which
    of the two tools to run (the server already knows), which avoids a second, non-deterministic model
    invocation. Each FunctionTool then makes exactly ONE bounded model call for its own reasoning.
    """

    name: str = AGENT_NAME
    model: str = AGENT_MODEL
    tools: list[str] = field(default_factory=lambda: list(TOOL_FNS))
    framework: str = "google.adk"
    adk_agent: Any = None  # the live google.adk LlmAgent when the SDK is bound; None in this environment

    def run(
        self,
        capability: str,
        payload: dict[str, Any] | Any,
        model_fn: Callable[..., Any] | None = None,
    ) -> Any:
        """Execute the named FunctionTool. This is what makes delegation REAL — the server calls
        agent.run(...), not the bare functions. Live: when adk_agent is bound and no test model_fn is
        injected, the call is routed through the ADK Runner (seam); otherwise the FunctionTool callable
        is invoked directly (identical result, no SDK required).

        Wrapped in a tool-execution span (§5.2) and structured logging (§5.1).
        """
        from runtime import bind_logger, tool_execution_span

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
                return fn(payload["spec"], payload["plan"], model_fn=model_fn)
            return fn(payload, model_fn=model_fn)


def _run_via_adk_runner(
    adk_agent: Any, capability: str, payload: dict[str, Any] | Any
) -> None:  # pragma: no cover - live seam
    """LIVE seam: run the bound ADK LlmAgent's FunctionTool via the ADK Runner. Bound at deploy time;
    in this environment google.adk is not installed so this path is never taken."""
    from google.adk.runners import Runner  # noqa: F401

    raise NotImplementedError(
        "Bind the ADK Runner to execute solution_accelerator_agent's FunctionTool on Cloud Run."
    )


def build_solution_accelerator_agent() -> SolutionAcceleratorAgent:
    """Construct the ONE Solution Accelerator Agent, binding the live google.adk `LlmAgent` (with both
    FunctionTools) into `adk_agent` when the SDK is available. Always returns a runnable agent object."""
    adk = None
    try:  # pragma: no cover - live ADK binding
        from google.adk.agents import LlmAgent
        from google.adk.tools import FunctionTool  # type: ignore[attr-defined]

        adk = LlmAgent(
            name=AGENT_NAME,
            model=AGENT_MODEL,
            instruction=(
                "You are the Solution Accelerator Agent. recommend_architecture designs an architecture "
                "from a spec+plan; create_epic_signal_ledger extracts a span-traced Epic Signal Ledger "
                "from a Rally Epic. Run exactly the tool the server requests (direct dispatch)."
            ),
            tools=[
                FunctionTool(recommend_architecture),
                FunctionTool(create_epic_signal_ledger),
            ],
        )
    except Exception:
        adk = None
    return SolutionAcceleratorAgent(adk_agent=adk)


def delegate(
    capability: str,
    payload: dict[str, Any] | Any,
    model_fn: Callable[..., Any] | None = None,
) -> Any:
    """The MCP server's delegation entry point. Builds the Solution Accelerator Agent and RUNS it —
    the agent object dispatches to the named FunctionTool (no LLM router; see SolutionAcceleratorAgent.run).

    capability:
      - "recommend_architecture"    → payload {"spec","plan"} → ArchitectureSelections
      - "create_epic_signal_ledger" → payload = epic dict | Epic → EpicSignalLedger
    """
    return build_solution_accelerator_agent().run(
        capability, payload, model_fn=model_fn
    )
