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
    ARTIFACT_PORT = int(os.getenv("ARTIFACT_PORT", "9004"))
    VERIFIER_PORT = int(os.getenv("VERIFIER_PORT", "9005"))
    print("Config initialized with ports:", RETRIEVER_PORT, GENERATOR_PORT, REVIEWER_PORT, ORCHESTRATOR_PORT, ARTIFACT_PORT)
    
    # Agent URLs (for local orchestration)
    RETRIEVER_URL = f"http://localhost:{RETRIEVER_PORT}"
    GENERATOR_URL = f"http://localhost:{GENERATOR_PORT}"
    REVIEWER_URL = f"http://localhost:{REVIEWER_PORT}"
    ARTIFACT_URL = f"http://localhost:{ARTIFACT_PORT}"
    VERIFIER_URL = f"http://localhost:{VERIFIER_PORT}"
    
    # GCS Configuration
    GCS_CONFIG_BUCKET = os.getenv("GCS_CONFIG_BUCKET", "engen-config")
    GCS_IAC_TEMPLATES_BUCKET = os.getenv("GCS_IAC_TEMPLATES_BUCKET", "engen-iac-templates")
    COMPONENT_MAPPING_FILE = os.getenv("COMPONENT_MAPPING_FILE", "component_mapping.json")
