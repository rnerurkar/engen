"""
Retrieval Agent - Handles information retrieval and pattern matching.
"""

import os
import sys
import asyncio
import uvicorn

# Add serving-service to path for lib imports
serving_service_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if serving_service_dir not in sys.path:
    sys.path.insert(0, serving_service_dir)

from lib.config import Config
from lib.adk_core import ADKAgent, AgentRequest, setup_logging

from google.cloud import firestore
from google.cloud import discoveryengine_v1 as discoveryengine


class RetrievalAgent(ADKAgent):
    def __init__(self, port: int = 8082, config: dict = None):
        super().__init__("RetrievalAgent", port=port)
        self.db = firestore.Client()
        self.config = config or {}
        self.collection_name = self.config.get('firestore_collection', 'patterns')
        
        # Initialize Discovery Engine client for semantic search
        if self.config.get('search_datastore'):
            self.search_client = discoveryengine.SearchServiceClient()
            self.serving_config = (
                f"projects/{self.config.get('project_id')}/"
                f"locations/global/collections/default_collection/"
                f"dataStores/{self.config.get('search_datastore')}/"
                f"servingConfigs/default_search"
            )
        else:
            self.search_client = None
            self.serving_config = None

    async def process(self, request: AgentRequest) -> dict:
        desc = request.payload.get('description') or request.payload.get('desc', '')
        
        # 1. Semantic Search using Vertex AI Discovery Engine
        donor_id = await self._semantic_search(desc)
        
        if not donor_id:
            return {"donor_id": None, "sections": {}, "error": "No matching patterns found"}
        
        # 2. Hydrate from Firestore
        docs = self.db.collection(self.collection_name).document(donor_id).collection('sections').stream()
        context = {}
        for doc in docs:
            data = doc.to_dict()
            section_name = data.get('section_name', doc.id)
            context[section_name] = data
        
        return {"donor_id": donor_id, "sections": context}

    async def _semantic_search(self, query: str) -> str:
        """Perform semantic search to find best matching pattern"""
        if not self.search_client or not self.serving_config:
            self.logger.warning("Search client not configured, using fallback")
            # Fallback: return first pattern from Firestore
            patterns = self.db.collection(self.collection_name).limit(1).stream()
            for pat in patterns:
                return pat.id
            return None
        
        try:
            request = discoveryengine.SearchRequest(
                serving_config=self.serving_config,
                query=query,
                page_size=1
            )
            response = self.search_client.search(request)
            
            for result in response.results:
                # Extract pattern ID from document
                doc_data = result.document.derived_struct_data
                return doc_data.get('pattern_id', result.document.id)
            
            return None
        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return None

    async def check_dependencies(self) -> dict:
        """Check Firestore and Discovery Engine availability"""
        deps = {}
        
        # Check Firestore
        try:
            # Quick read test
            test_ref = self.db.collection(self.collection_name).limit(1)
            list(test_ref.stream())
            deps["firestore"] = {"healthy": True, "critical": True}
        except Exception as e:
            deps["firestore"] = {"healthy": False, "critical": True, "error": str(e)}
        
        # Check Discovery Engine (if configured)
        if self.search_client:
            try:
                # We can't easily test without a query, so just check client exists
                deps["discovery_engine"] = {"healthy": True, "critical": False}
            except Exception as e:
                deps["discovery_engine"] = {"healthy": False, "critical": False, "error": str(e)}
        
        return deps

    def get_supported_tasks(self):
        return ["find_donor", "search", "retrieve"]

    def get_description(self):
        return "Retrieves relevant architecture patterns using semantic search"


async def main():
    """Main entry point"""
    config = Config.get_agent_config("retrieval")
    setup_logging(config["log_level"])
    
    agent = RetrievalAgent(port=config["port"], config=config)
    await agent.start()
    await agent.run_async(port=config["port"])


if __name__ == "__main__":
    asyncio.run(main())

