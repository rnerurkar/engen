"""
Retrieval Agent - Handles information retrieval and pattern matching.
"""

import os
import sys
import asyncio
import base64
import uvicorn
from typing import List, Dict, Set, Optional

# Add serving-service to path for lib imports
serving_service_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if serving_service_dir not in sys.path:
    sys.path.insert(0, serving_service_dir)

from lib.config import Config
from lib.adk_core import ADKAgent, AgentRequest, setup_logging

from google.cloud import firestore
from google.cloud import discoveryengine_v1 as discoveryengine
import vertexai
from vertexai.vision_models import MultiModalEmbeddingModel, Image
from google.cloud import aiplatform


class RetrievalAgent(ADKAgent):
    def __init__(self, port: int = 8082, config: dict = None):
        super().__init__("RetrievalAgent", port=port)
        self.db = firestore.Client()
        self.config = config or {}
        self.collection_name = self.config.get('firestore_collection', 'patterns')
        
        # Initialize Vertex AI
        vertexai.init(project=self.config.get('project_id'), location=self.config.get('location', 'us-central1'))
        
        # 1. Load Multimodal Embedding Model
        try:
            self.embedding_model = MultiModalEmbeddingModel.from_pretrained("multimodalembedding")
            self.logger.info("Multimodal embedding model loaded")
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None

        # 2. Initialize Vector Search Endpoint
        if self.config.get('vector_endpoint_id'):
            self.vector_endpoint = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=self.config.get('vector_endpoint_id')
            )
            self.deployed_index_id = self.config.get('deployed_index_id')
        else:
            self.vector_endpoint = None

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
        """
        Payload expectations:
        {
            "description": "text description...", 
            "image_base64": "optional_base64_string...",
            "top_k": 5
        }
        """
        desc = request.payload.get('description') or request.payload.get('desc', '')
        image_data = request.payload.get('image_base64')
        top_k = request.payload.get('top_k', 5)
        
        # 1. Hybrid Search (Text + Visual)
        ranked_pattern_ids = await self._hybrid_search(desc, image_data, top_k)
        
        if not ranked_pattern_ids:
            return {"donor_id": None, "sections": {}, "error": "No matching patterns found"}
        
        # Select best match
        best_match_id = ranked_pattern_ids[0]
        
        # 2. Hydrate from Firestore
        context = {}
        try:
            docs = self.db.collection(self.collection_name).document(best_match_id).collection('sections').stream()
            for doc in docs:
                data = doc.to_dict()
                section_name = data.get('section_name', doc.id)
                context[section_name] = data
        except Exception as e:
            self.logger.error(f"Failed to hydrate content for {best_match_id}: {e}")
        
        return {
            "donor_id": best_match_id, 
            "match_confidence": "high" if len(ranked_pattern_ids) > 0 else "none",
            "sections": context,
            "alternatives": ranked_pattern_ids[1:5]
        }

    async def _hybrid_search(self, text: str, image_b64: Optional[str], top_k: int) -> List[str]:
        """
        Queries Discovery Engine (Text) and Vector Search (Image) 
        and fuses results using Reciprocal Rank Fusion (RRF).
        """
        tasks = []
        
        # Task A: Text Search (Discovery Engine)
        if text:
            tasks.append(self._search_text_discovery(text))
        
        # Task B: Image Search (Vector Search)
        if image_b64 and self.vector_endpoint:
            tasks.append(self._search_image_vector(image_b64))
            
        if not tasks:
            return []

        # Run searches in parallel
        results_list = await asyncio.gather(*tasks)
        
        # Merge results using RRF
        return self._reciprocal_rank_fusion(results_list, k=60)

    async def _search_text_discovery(self, text: str) -> List[str]:
        """Search text using Discovery Engine"""
        if not self.search_client:
            return []
        try:
            request = discoveryengine.SearchRequest(
                serving_config=self.serving_config,
                query=text,
                page_size=10
            )
            response = await asyncio.to_thread(self.search_client.search, request)
            # Extract Pattern IDs (assumed to be stored in 'pattern_id' field or id)
            ids = []
            for result in response.results:
                data = result.document.derived_struct_data
                pattern_id = data.get('pattern_id') or result.document.id
                # Handles "desc_WR-001" format from Stream A
                if pattern_id.startswith('desc_'):
                    pattern_id = pattern_id.replace('desc_', '')
                ids.append(pattern_id)
            return ids
        except Exception as e:
            self.logger.error(f"Discovery Engine search error: {e}")
            return []

    async def _search_image_vector(self, b64_str: str) -> List[str]:
        """Generates image embedding and searches vector index"""
        if not self.embedding_model or not self.vector_endpoint:
            return []
        try:
            image = Image(base64.b64decode(b64_str))
            embeddings = self.embedding_model.get_embeddings(
                image=image
            )
            response = self.vector_endpoint.find_neighbors(
                deployed_index_id=self.deployed_index_id,
                queries=[embeddings.image_embedding],
                num_neighbors=10
            )
            # IDs in Vector Search are usually "img_<pattern_id>_<uuid>"
            pattern_ids = []
            for neighbor in response[0]:
                raw_id = neighbor.id
                # Format: img_WR-001_a1b2c3d4 - Extract middle part
                parts = raw_id.split('_')
                if len(parts) >= 2:
                    p_id = "_".join(parts[1:-1])
                    pattern_ids.append(p_id)
            return pattern_ids
        except Exception as e:
            self.logger.error(f"Image search error: {e}")
            return []

    def _reciprocal_rank_fusion(self, lists_of_ids: List[List[str]], k: int = 60) -> List[str]:
        """
        Combines multiple ranked lists into one using RRF.
        Score = sum(1 / (k + rank))
        """
        scores: Dict[str, float] = {}
        
        for current_list in lists_of_ids:
            for rank, item_id in enumerate(current_list):
                if not item_id: continue
                if item_id not in scores:
                    scores[item_id] = 0
                scores[item_id] += 1 / (k + rank)
        
        # Sort by score descending
        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [item[0] for item in sorted_items]

    async def _semantic_search(self, query: str) -> str:
        """Deprecated: Wrapper for simplified calls"""
        ids = await self._search_text_discovery(query)
        return ids[0] if ids else None

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

