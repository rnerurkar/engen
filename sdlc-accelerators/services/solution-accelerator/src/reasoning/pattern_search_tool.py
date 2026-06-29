"""ADK FunctionTool — pattern retrieval for the greenfield architecture recommender.

The recommender LlmAgent decides what to query and when, then reasons over the candidates. Wraps
the VertexSearchClient seam (Pattern Catalog over Vertex AI Search) via the shared
pattern_search_core. Retrieval only — selection remains the LlmAgent's reasoning; the deterministic
stages stay sequential steps, not tools.
"""

from __future__ import annotations

from typing import Any

from clients.vertex_search import VertexSearchClient

from .pattern_search_core import search_patterns_safe


def make_pattern_search_tool(client: VertexSearchClient | None = None) -> Any:
    """Build an ADK FunctionTool that searches the Pattern Catalog. `client` is injectable for
    tests; production uses the live VertexSearchClient seam."""
    from google.adk.tools import FunctionTool  # type: ignore[attr-defined]

    search_client = client or VertexSearchClient()

    def search_architecture_patterns(ordering_signals: list[str]) -> dict[str, Any]:
        """Search the Pattern Catalog for candidate ADK architecture patterns.

        Use this to retrieve composition patterns (SequentialAgent, ParallelAgent, LoopAgent,
        HITL, etc.) that match the spec's ordering signals. Returns candidates only — you must
        still select and justify the composition.

        Args:
            ordering_signals: words describing the required control flow (e.g. ["first", "then",
                "in parallel", "loop until", "human approval"]).

        Returns:
            {"patterns": [ ... ]} — candidate patterns (empty until the corpus is ingested).
        """
        return search_patterns_safe(search_client, ordering_signals)

    return FunctionTool(func=search_architecture_patterns)
