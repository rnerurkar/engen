"""
Service HA/DR Retriever — Vertex AI Search Edition
---------------------------------------------------
Retrieves service-level HA/DR documentation from a dedicated Vertex AI Search
data store to provide grounding context for pattern-level HA/DR generation.

Uses **hybrid retrieval**: structured metadata filter (exact service name)
combined with vector/semantic search.  This prevents cross-contamination
between services that share similar HA/DR vocabulary.
"""

import logging
from typing import Dict, Any, List, Optional

from google.cloud import discoveryengine_v1 as discoveryengine

logger = logging.getLogger(__name__)


class ServiceHADRRetriever:
    """
    Retrieves service-level HA/DR documentation chunks from Vertex AI Search.

    Each chunk in the datastore carries structured metadata:
      - service_name       (exact canonical name)
      - service_type       (Compute | Storage | Database | Network)
      - dr_strategy        (one of DR_STRATEGIES)
      - lifecycle_phase    (Initial Provisioning | Failover | Failback)

    Retrieval strategy:
      1. Metadata filter locks to the correct service (and optionally strategy).
      2. Semantic/vector component ranks the matching chunks by relevance.
    """

    # The four DR strategies every pattern document must cover
    DR_STRATEGIES = [
        "Backup and Restore",
        "Pilot Light On Demand",
        "Pilot Light Cold Standby",
        "Warm Standby",
    ]

    # The three lifecycle phases within each DR strategy
    LIFECYCLE_PHASES = [
        "Initial Provisioning",
        "Failover",
        "Failback",
    ]

    def __init__(
        self,
        project_id: str,
        location: str = "global",
        data_store_id: str = "service-hadr-datastore",
        collection: str = "default_collection",
    ):
        self.project_id = project_id
        self.location = location
        self.data_store_id = data_store_id
        self.collection = collection
        self._init_client()

    # ─── Initialisation ──────────────────────────────────────────────────

    def _init_client(self):
        try:
            self.search_client = discoveryengine.SearchServiceClient()
            self.serving_config = (
                f"projects/{self.project_id}"
                f"/locations/{self.location}"
                f"/collections/{self.collection}"
                f"/dataStores/{self.data_store_id}"
                f"/servingConfigs/default_search"
            )
            logger.info(
                f"ServiceHADRRetriever initialised — datastore={self.data_store_id}"
            )
        except Exception as e:
            logger.error(f"Failed to initialise Vertex AI Search client: {e}")
            self.search_client = None

    # ─── Single-service retrieval ────────────────────────────────────────

    def retrieve_service_hadr_docs(
        self,
        service_name: str,
        service_type: Optional[str] = None,
        dr_strategy: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve HA/DR chunks for a specific service, optionally scoped to a
        single DR strategy.

        Returns a list of dicts, each containing ``content`` and metadata keys.
        """
        if not self.search_client:
            logger.error("Search client not available")
            return []

        # ── Build metadata filter ────────────────────────────────────────
        filter_parts = [f'service_name = "{service_name}"']
        if service_type:
            filter_parts.append(f'service_type = "{service_type}"')
        if dr_strategy:
            filter_parts.append(f'dr_strategy = "{dr_strategy}"')
        filter_str = " AND ".join(filter_parts)

        # ── Build semantic query ─────────────────────────────────────────
        query_text = f"{service_name} HA/DR"
        if dr_strategy:
            query_text += (
                f" {dr_strategy} behaviour during provisioning failover failback"
            )

        try:
            request = discoveryengine.SearchRequest(
                serving_config=self.serving_config,
                query=query_text,
                filter=filter_str,
                page_size=top_k,
                content_search_spec=discoveryengine.SearchRequest.ContentSearchSpec(
                    snippet_spec=discoveryengine.SearchRequest.ContentSearchSpec.SnippetSpec(
                        return_snippet=True,
                        max_snippet_count=3,
                    ),
                    extractive_content_spec=discoveryengine.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
                        max_extractive_answer_count=5,
                        max_extractive_segment_count=5,
                    ),
                ),
                query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
                    condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO
                ),
            )

            response = self.search_client.search(request)
            results: List[Dict[str, Any]] = []

            for result in response.results:
                doc = result.document
                struct_data = dict(doc.struct_data) if doc.struct_data else {}

                # Extract the most relevant text from derived/extractive data
                content = ""
                if doc.derived_struct_data:
                    derived = dict(doc.derived_struct_data)
                    for ans in derived.get("extractive_answers", []):
                        content += dict(ans).get("content", "") + "\n"
                    if not content:
                        for snip in derived.get("snippets", []):
                            content += dict(snip).get("snippet", "") + "\n"

                results.append(
                    {
                        "service_name": struct_data.get(
                            "service_name", service_name
                        ),
                        "service_type": struct_data.get("service_type", ""),
                        "dr_strategy": struct_data.get("dr_strategy", ""),
                        "lifecycle_phase": struct_data.get(
                            "lifecycle_phase", ""
                        ),
                        "content": content.strip()
                        or struct_data.get("content", ""),
                        "document_id": doc.id,
                    }
                )

            logger.info(
                f"Retrieved {len(results)} HA/DR chunks for "
                f"service='{service_name}' (filter: {filter_str})"
            )
            return results

        except Exception as e:
            logger.error(
                f"Search failed for service '{service_name}': {e}"
            )
            return []

    # ─── Bulk retrieval (all services × all strategies) ──────────────────

    def retrieve_all_services_hadr(
        self,
        service_names: List[str],
        service_types: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """
        Retrieve HA/DR docs for every service in the pattern, organised as::

            {
                "Amazon RDS": {
                    "Backup and Restore": [chunk, …],
                    "Pilot Light On Demand": [chunk, …],
                    …
                },
                "AWS Lambda": { … },
            }

        This is the main entry-point called by the Orchestrator / HA/DR
        generation step.
        """
        all_docs: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

        for svc_name in service_names:
            svc_type = (service_types or {}).get(svc_name)
            all_docs[svc_name] = {}

            for strategy in self.DR_STRATEGIES:
                chunks = self.retrieve_service_hadr_docs(
                    service_name=svc_name,
                    service_type=svc_type,
                    dr_strategy=strategy,
                    top_k=5,
                )
                all_docs[svc_name][strategy] = chunks

        total_chunks = sum(
            len(chunks)
            for svc_strategies in all_docs.values()
            for chunks in svc_strategies.values()
        )
        logger.info(
            f"Retrieved {total_chunks} total HA/DR chunks "
            f"across {len(service_names)} services"
        )
        return all_docs
