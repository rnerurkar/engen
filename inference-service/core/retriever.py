import logging
import os
from google.cloud import discoveryengine_v1 as discoveryengine
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class VertexRetriever:
    """
    Retrieves full reference documents from Vertex AI Search to act as 
    'Donor Patterns' for style transfer.
    """
    def __init__(self, project_id: str, location: str, data_store_id: str):
        self.project_id = project_id
        self.location = location
        self.data_store_id = data_store_id
        self.client = discoveryengine.SearchServiceClient()
        self.doc_client = discoveryengine.DocumentServiceClient()
        self.serving_config = f"projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}/servingConfigs/default_search"
        self.branch = f"projects/{project_id}/locations/{location}/collections/default_collection/dataStores/{data_store_id}/branches/default_branch"

    def get_best_donor_pattern(self, query: str, description: str = "") -> Optional[Dict[str, str]]:
        """
        Finds the most relevant existing pattern to use as a style template.
        Returns the full HTML content and metadata.
        """
        try:
            # Hybrid Search Query: Combine Title + Structural Description
            search_query = f"{query} {description}".strip()
            
            # 1. Search for matches
            request = discoveryengine.SearchRequest(
                serving_config=self.serving_config,
                query=search_query,
                page_size=1, # We only need one "Gold Standard" to mimic
                query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(condition="AUTO")
            )
            response = self.client.search(request)
            
            if not response.results:
                logger.warning("No reference patterns found.")
                return None

            hit = response.results[0]
            doc_id = hit.document.id
            
            # 2. Fetch the full document content explicitly
            full_doc_name = f"{self.branch}/documents/{doc_id}"
            full_document = self.doc_client.get_document(name=full_doc_name)
            
            # Assuming raw_bytes contains the HTML if ingested as such
            # Fallback to text content if raw_bytes is not set or structured data
            html_content = ""
            if full_document.content.raw_bytes:
                html_content = full_document.content.raw_bytes.decode("utf-8")
            elif full_document.content.uri:
                # If stored as URI (not expected in this pipeline but handling safely)
                 html_content = f"Reference URI: {full_document.content.uri}"
            
            logger.info(f"Retrieved donor pattern: {doc_id}")
            
            return {
                "id": doc_id,
                "title": full_document.struct_data.get("title", "Unknown"),
                "html_content": html_content
            }
            
        except Exception as e:
            logger.error(f"Error retrieving donor pattern: {e}")
            return None
