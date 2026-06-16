"""Shared core for pattern-retrieval ADK tools (greenfield + brownfield).

Both archetypes wrap the same VertexSearchClient seam with the same "degrade to empty on
NotImplementedError" behavior; only their tool signatures differ (greenfield: ordering signals;
brownfield: per-integration target/categories/r-factor). This module holds the shared wrap so the
two tool factories don't duplicate it.
"""
from __future__ import annotations

from clients.vertex_search import VertexSearchClient


def search_patterns_safe(client: VertexSearchClient, query_terms: list[str]) -> dict:
    """Run a Pattern Catalog search and shape the result. Degrades to an empty candidate list
    when the live call isn't configured / the corpus isn't ingested (never raises to the agent)."""
    try:
        patterns = client.search_patterns(query_terms)
    except NotImplementedError:
        patterns = []
    return {"patterns": patterns}
