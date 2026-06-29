"""ADK FunctionTool — transition-pattern retrieval for the brownfield pattern recommender.

The recommender LlmAgent decides what to query per integration and reasons over the candidates.
Wraps the platform's VertexSearchClient seam via the shared pattern_search_core. Retrieval only —
the deterministic substitution and ADR-compliance stages remain sequential steps (not tools).
"""

from __future__ import annotations

import os
import sys
from typing import Any, cast

# Reuse the platform's VertexSearchClient + shared core via the centralized path bootstrap.
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
import _srcpaths  # noqa: E402

_srcpaths.ensure("solution-accelerator")


def make_transition_pattern_search_tool(client: Any = None) -> Any:
    """Build an ADK FunctionTool that searches the Pattern Catalog for transition patterns.
    `client` is injectable for tests; production uses the live VertexSearchClient seam."""
    from clients.vertex_search import VertexSearchClient
    from google.adk.tools import FunctionTool  # type: ignore[attr-defined]
    from reasoning.pattern_search_core import search_patterns_safe

    search_client = client or VertexSearchClient()

    def search_transition_patterns(
        target_tech: str, functional_categories: list[str], r_factor: str
    ) -> dict[str, Any]:
        """Search the Pattern Catalog for candidate migration transition patterns.

        Use this per integration to retrieve transition patterns (strangler-fig, dual-publish,
        blue-green, etc.) that fit the chosen target technology, functional categories, and
        R-factor. Returns candidates only — you must still select and justify the pattern, and
        flag low-confidence selections for review.

        Args:
            target_tech: the chosen target technology (e.g. "aws-sqs").
            functional_categories: functional categories of the integration (e.g. ["messaging"]).
            r_factor: one of rehost, replatform, refactor, rearchitect, retire.

        Returns:
            {"patterns": [ ... ]} — candidate transition patterns (empty until the corpus is ingested).
        """
        return cast(
            "dict[str, Any]",
            search_patterns_safe(
                search_client, [target_tech, r_factor, *functional_categories]
            ),
        )

    return FunctionTool(func=search_transition_patterns)
