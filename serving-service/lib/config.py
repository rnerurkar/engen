# lib/config.py
import os
from typing import Optional
from pydantic_settings import BaseSettings

class ServiceConfig(BaseSettings):
    """
    Centralized configuration for all Smart Architect Agents.
    Reads from Environment Variables injected by Cloud Run.
    """
    
    # --- Infrastructure Identity ---
    GCP_PROJECT_ID: str
    GCP_LOCATION: str = "us-central1"
    
    # --- Knowledge Graph Resources ---
    # Used by Retrieval Agent
    VERTEX_SEARCH_DATA_STORE_ID: Optional[str] = None
    VERTEX_VECTOR_INDEX_ENDPOINT: Optional[str] = None
    VERTEX_DEPLOYED_INDEX_ID: Optional[str] = None
    
    # Used by Retrieval & Writer Agents
    FIRESTORE_DATABASE: str = "(default)"
    FIRESTORE_COLLECTION_PATTERNS: str = "patterns"
    
    # Used by Vision Agent
    GCS_IMAGE_BUCKET: Optional[str] = None

    # --- Agent Swarm Topology (Service Discovery) ---
    # Used by Orchestrator to route tasks
    VISION_AGENT_URL: Optional[str] = None
    RETRIEVAL_AGENT_URL: Optional[str] = None
    WRITER_AGENT_URL: Optional[str] = None
    REVIEWER_AGENT_URL: Optional[str] = None

    # --- ADK Settings ---
    PORT: int = 8080
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @classmethod
    def get_agent_config(cls, agent_name: str) -> dict:
        """Get configuration for a specific agent"""
        instance = cls()
        
        # Agent-specific port overrides
        agent_ports = {
            "orchestrator": int(os.getenv("ORCHESTRATOR_PORT", 8080)),
            "vision": int(os.getenv("VISION_PORT", 8081)),
            "retrieval": int(os.getenv("RETRIEVAL_PORT", 8082)),
            "writer": int(os.getenv("WRITER_PORT", 8083)),
            "reviewer": int(os.getenv("REVIEWER_PORT", 8084)),
        }
        
        return {
            "name": agent_name,
            "port": agent_ports.get(agent_name, instance.PORT),
            "log_level": instance.LOG_LEVEL,
            "project_id": instance.GCP_PROJECT_ID,
            "location": instance.GCP_LOCATION,
            "firestore_collection": instance.FIRESTORE_COLLECTION_PATTERNS,
            "vector_endpoint": instance.VERTEX_VECTOR_INDEX_ENDPOINT,
            "deployed_index_id": instance.VERTEX_DEPLOYED_INDEX_ID,
            "search_datastore": instance.VERTEX_SEARCH_DATA_STORE_ID,
            "gcs_bucket": instance.GCS_IMAGE_BUCKET,
        }

# Singleton instance
config = ServiceConfig()

# Alias for backward compatibility
Config = ServiceConfig