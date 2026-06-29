"""The brownfield Solution Accelerator Agent — one ADK agent the MCP server delegates to, with two
FunctionTools: recommend_architecture and create_epic_signal_ledger."""

from __future__ import annotations

from .solution_accelerator_agent import (  # noqa: F401
    AGENT_NAME,
    build_solution_accelerator_agent,
    create_epic_signal_ledger,
    delegate,
    recommend_architecture,
)
