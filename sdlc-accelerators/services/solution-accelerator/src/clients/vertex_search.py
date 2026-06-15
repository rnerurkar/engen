"""Vertex AI Search client — RAG retrieval over the Pattern Catalog + Skill Catalog data stores.

INTERFACE + query/result shaping are real and testable via an injected `_search` seam.
The live Discovery Engine (Vertex AI Search) network call is written below but COMMENTED OUT.
Per root CLAUDE.md, all external calls go through clients/base.with_retry.
"""
from __future__ import annotations

from collections.abc import Callable

from .base import with_retry


class VertexSearchClient:
    def __init__(self, project_id: str | None = None, location: str = "global",
                 pattern_data_store: str = "sdlc-pattern-catalog",
                 skill_data_store: str = "sdlc-skill-catalog",
                 _search: Callable[[str, str], list] | None = None):
        self.project_id = project_id
        self.location = location
        self.pattern_data_store = pattern_data_store
        self.skill_data_store = skill_data_store
        self._search = _search   # test injection seam: (data_store_id, query) -> list[dict]

    def search_patterns(self, signals: list[str]) -> list[dict]:
        """Semantic search over the Pattern Catalog. Returns matched patterns + metadata."""
        query = " ".join(signals)
        return self._run(self.pattern_data_store, query)

    def search_tools(self, data_sources: list[str]) -> list[dict]:
        """Semantic search over the Skill Catalog (skill metadata + SHA/version provenance)."""
        query = " ".join(data_sources)
        return self._run(self.skill_data_store, query)

    def _run(self, data_store_id: str, query: str) -> list[dict]:
        if self._search is not None:
            return with_retry(lambda: self._search(data_store_id, query))
        return self._live_search(data_store_id, query)

    def _live_search(self, data_store_id: str, query: str) -> list[dict]:
        """The actual Vertex AI Search (Discovery Engine) call. COMMENTED OUT until wired.

        TO WIRE (checklist):
          1. `pip install google-cloud-discoveryengine`
          2. Supply self.project_id + self.location + the data_store_id (created by the
             catalog-ingestion pipeline). Returns empty until the corpus is ingested.
          3. Credentials: Application Default Credentials (ADC) with the
             Discovery Engine Viewer role.
          4. Ensure egress to discoveryengine.googleapis.com.
          5. Uncomment the body and wrap the search call in with_retry(...).
        """
        # from google.cloud import discoveryengine_v1 as de
        #
        # client = de.SearchServiceClient()
        # serving_config = (
        #     f"projects/{self.project_id}/locations/{self.location}"
        #     f"/collections/default_collection/dataStores/{data_store_id}"
        #     f"/servingConfigs/default_config"
        # )
        # request = de.SearchRequest(serving_config=serving_config, query=query, page_size=10)
        # results = []
        # for r in client.search(request=request).results:
        #     doc = r.document
        #     struct = dict(doc.struct_data) if doc.struct_data else {}
        #     results.append({"id": doc.id, **struct})
        # return results
        raise NotImplementedError(
            "Vertex AI Search live call is written but commented out in _live_search. "
            "Uncomment it (+ google-cloud-discoveryengine + credentials + ingested corpus), "
            "or inject _search in tests."
        )
