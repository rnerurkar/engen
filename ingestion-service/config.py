import os

class Config:
    # GCP
    PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    LOCATION = os.getenv("GCP_LOCATION", "us-central1")
    GCS_BUCKET = os.getenv("GCS_IMAGE_BUCKET")
    
    # Vertex AI
    SEARCH_DATA_STORE_ID = os.getenv("VERTEX_SEARCH_DS_ID")
    VECTOR_INDEX_ENDPOINT = os.getenv("VERTEX_VECTOR_ENDPOINT_ID")
    DEPLOYED_INDEX_ID = os.getenv("VERTEX_DEPLOYED_INDEX_ID")
    
    # Firestore
    FIRESTORE_COLLECTION = "patterns"
    
    # SharePoint (Azure AD App)
    AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
    AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
    SP_SITE_ID = os.getenv("SP_SITE_ID")
    SP_LIST_ID = os.getenv("SP_LIST_ID")
