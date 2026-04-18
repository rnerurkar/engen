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
    
    # Agent Ports (retained for standalone / Cloud Run deployments)
    ORCHESTRATOR_PORT = int(os.getenv("ORCHESTRATOR_PORT", "9000"))
    
    # GCS Configuration
    GCS_CONFIG_BUCKET = os.getenv("GCS_CONFIG_BUCKET", "engen-config")
    GCS_IAC_TEMPLATES_BUCKET = os.getenv("GCS_IAC_TEMPLATES_BUCKET", "engen-iac-templates")
    COMPONENT_MAPPING_FILE = os.getenv("COMPONENT_MAPPING_FILE", "component_mapping.json")

    # Service HA/DR Configuration
    SERVICE_HADR_DATA_STORE_ID = os.getenv("SERVICE_HADR_DS_ID", "service-hadr-datastore")
    SERVICE_HADR_GCS_BUCKET = os.getenv("SERVICE_HADR_GCS_BUCKET", "engen-service-hadr-images")

    # HA/DR Diagram Storage (SVG, draw.io XML, PNG)
    HADR_DIAGRAM_GCS_BUCKET = os.getenv("HADR_DIAGRAM_GCS_BUCKET", "engen-hadr-diagrams")

    # AlloyDB Configuration (replaces CloudSQL)
    # Instance URI format: projects/<PROJECT>/locations/<REGION>/clusters/<CLUSTER>/instances/<INSTANCE>
    ALLOYDB_INSTANCE = os.getenv(
        "ALLOYDB_INSTANCE",
        "projects/engen-project/locations/us-central1/clusters/engen-cluster/instances/engen-primary"
    )
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "postgres")
    DB_NAME = os.getenv("DB_NAME", "reviews_db")
