import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Service Configuration
    PROJECT_ID = os.getenv("GCP_PROJECT_ID", "engen-project")
    LOCATION = os.getenv("GCP_LOCATION", "us-central1")
    
    # Vertex AI Search
    DATA_STORE_ID = os.getenv("VERTEX_DATA_STORE_ID", "patterns-ds")
    
    # Agent Ports
    RETRIEVER_PORT = int(os.getenv("RETRIEVER_PORT", "9001"))
    GENERATOR_PORT = int(os.getenv("GENERATOR_PORT", "9002"))
    REVIEWER_PORT = int(os.getenv("REVIEWER_PORT", "9003"))
    ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "9000"))
    print("Config initialized with ports:", RETRIEVER_PORT, GENERATOR_PORT, REVIEWER_PORT, ORCHESTRATOR_PORT)
    
    # Agent URLs (for local orchestration)
    RETRIEVER_URL = f"http://localhost:{RETRIEVER_PORT}"
    GENERATOR_URL = f"http://localhost:{GENERATOR_PORT}"
    REVIEWER_URL = f"http://localhost:{REVIEWER_PORT}"
