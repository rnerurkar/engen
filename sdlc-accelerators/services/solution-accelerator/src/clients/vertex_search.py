"""vertex_search client wrapper.
INTERFACE is real; the external call is a STUB marked TODO for live wiring.
Per root CLAUDE.md, all calls go through clients/base.with_retry.
"""
from __future__ import annotations

from .base import with_retry


class VertexSearchClient:
    def __init__(self, endpoint: str | None = None):
        self.endpoint = endpoint

    # TODO(live): replace stub bodies with real vertex_search SDK calls.

    def search_patterns(self, signals: list[str]) -> list[dict]:
        """Query the pattern + tool catalog. STUB returns empty; live wiring TODO."""
        return with_retry(lambda: [])

    def search_tools(self, data_sources: list[str]) -> list[dict]:
        return with_retry(lambda: [])
